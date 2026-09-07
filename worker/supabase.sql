-- Chat de diseños — Boss Padel
-- Tabla, permisos, storage y realtime. Idempotente: se puede correr de nuevo.

-- ─────────────────────────────────────────────────────────────── TABLA

create table if not exists public.disenos (
  id              uuid primary key default gen_random_uuid(),
  creado_en       timestamptz not null default now(),
  actualizado_en  timestamptz not null default now(),
  user_id         uuid references auth.users(id) on delete set null,

  -- lo que escribe la persona en el chat
  mensaje         text not null,
  formatos        text[] not null default array['post'],
  sede            text not null default 'Carrasco',
  quien           text,

  -- lo que completa el worker
  estado          text not null default 'pendiente'
                  check (estado in ('pendiente','generando','listo','error')),
  titulo          text,
  urls            text[],
  documentos      jsonb not null default '[]'::jsonb,
  videos          jsonb not null default '[]'::jsonb,
  adjuntos        jsonb not null default '[]'::jsonb,
  metricas        jsonb not null default '{}'::jsonb,
  copy            text,
  mensaje_agente  text
);

-- Se agrega acá además de en el create para las bases que ya existían antes
-- de que el sistema supiera generar presentaciones.
alter table public.disenos
  add column if not exists documentos jsonb not null default '[]'::jsonb;
alter table public.disenos
  add column if not exists videos jsonb not null default '[]'::jsonb;
alter table public.disenos
  add column if not exists adjuntos jsonb not null default '[]'::jsonb;
alter table public.disenos
  add column if not exists metricas jsonb not null default '{}'::jsonb;

comment on column public.disenos.mensaje is
  'El pedido en lenguaje natural. Es el campo que hace todo el trabajo.';
comment on column public.disenos.estado is
  'pendiente → generando → listo | error. El worker es el único que lo mueve.';
comment on column public.disenos.urls is
  'Las imágenes, en orden. El chat las muestra con un <img>.';
comment on column public.disenos.documentos is
  'Los PDF: [{nombre, url, peso}]. Van aparte de urls porque no se '
  'previsualizan en línea — el chat les da una tarjeta de descarga.';
comment on column public.disenos.videos is
  'Los reels: [{nombre, url, peso, duracion}]. Van aparte porque el chat los '
  'reproduce con un <video>, no los muestra como imagen ni solo para bajar.';
comment on column public.disenos.mensaje_agente is
  'Qué asumió o por qué falló. Sin aprobación humana, es la única red.';

create index if not exists disenos_pendientes_idx
  on public.disenos (creado_en) where estado = 'pendiente';
create index if not exists disenos_user_idx
  on public.disenos (user_id, creado_en desc);

-- Mantiene actualizado_en al día para que Realtime tenga con qué ordenar.
create or replace function public.tocar_actualizado_en()
returns trigger language plpgsql as $$
begin
  new.actualizado_en = now();
  return new;
end $$;

drop trigger if exists disenos_tocar on public.disenos;
create trigger disenos_tocar before update on public.disenos
  for each row execute function public.tocar_actualizado_en();

-- ─────────────────────────────────────────────────────────────── RLS

alter table public.disenos enable row level security;

-- Cada persona ve y crea sólo lo suyo. El worker usa service_role, que
-- saltea RLS por definición, así que no necesita política propia.
drop policy if exists "ver lo propio" on public.disenos;
create policy "ver lo propio" on public.disenos
  for select to authenticated using (auth.uid() = user_id);

drop policy if exists "crear lo propio" on public.disenos;
create policy "crear lo propio" on public.disenos
  for insert to authenticated with check (auth.uid() = user_id);

-- Nadie edita ni borra desde el frontend: el estado lo maneja el worker.

-- ─────────────────────────────────────────────────────────── STORAGE

insert into storage.buckets (id, name, public)
values ('disenos', 'disenos', true)
on conflict (id) do update set public = true;

-- Lectura pública para poder mostrar la imagen en el chat con un <img>.
drop policy if exists "leer disenos" on storage.objects;
create policy "leer disenos" on storage.objects
  for select using (bucket_id = 'disenos');

-- La escritura la hace sólo el worker con service_role.

-- ────────────────────────────────────────────────────────── REALTIME

-- Con esto el chat ve el cambio de estado sin refrescar ni hacer polling.
alter table public.disenos replica identity full;

do $$
begin
  if not exists (
    select 1 from pg_publication_tables
    where pubname = 'supabase_realtime'
      and schemaname = 'public' and tablename = 'disenos'
  ) then
    alter publication supabase_realtime add table public.disenos;
  end if;
end $$;
