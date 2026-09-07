-- El banco de fotos del cliente.
--
-- Se corre UNA VEZ en el Supabase de cada cliente. Es aditivo: no toca nada de
-- lo que ya anda.
--
-- ── Por qué una tabla y no una carpeta ────────────────────────────────────
--
-- El valor del banco no son los archivos: es lo que sabemos de cada foto.
-- Hoy eso vive en `referencias/fotos.json` dentro del worker y trae dos cosas
-- que ningún selector de archivos puede dar solo:
--
--   `foco`   el encuadre YA RESUELTO para cada formato. Sin esto el agente
--            adivina, y adivinar termina con la cara del sujeto cortada o
--            chocando contra el titular. Nos pasó.
--   `quien`  quién aparece. Es lo que permite cumplir «que sea con jugadoras»,
--            «sin gente» o «que no sea rubio» sin abrir una sola imagen.
--
-- Si el selector subiera la foto como un adjunto suelto, perderíamos las dos.
-- Por eso el banco es una tabla que leen los dos lados: la app para mostrar el
-- selector, y el worker para armar su `fotos.json`.

create table if not exists public.fotos (
  id           uuid primary key default gen_random_uuid(),
  creado_en    timestamptz not null default now(),
  user_id      uuid references auth.users(id) on delete set null,

  -- La clave con la que el agente la nombra en el spec. Sale del nombre del
  -- archivo, en minúsculas y sin espacios: `jugadora-saque`.
  clave        text not null,
  url          text not null,

  descripcion  text,
  -- Con qué se filtra en el selector: «cancha», «clase», «torneo», «lounge».
  etiquetas    text[] not null default '{}',

  -- Quién aparece. Estructura libre pero se espera:
  --   {"genero":"femenino","cantidad":"una persona","edad":"adulto",
  --    "apariencia":"pelo claro; remera azul"}
  quien        jsonb not null default '{}'::jsonb,

  -- El encuadre por formato, en `object-position` de CSS: {"post":"50% 30%"}.
  -- Arranca vacío y **se completa solo con el uso**: cuando el agente corrige
  -- un encuadre porque miró la pieza y la cara quedó cortada, lo guarda acá.
  -- La segunda vez que se usa esa foto, el problema ya está resuelto.
  foco         jsonb not null default '{}'::jsonb,

  ancho        int,
  alto         int,
  activa       boolean not null default true
);

create unique index if not exists fotos_clave_idx on public.fotos (clave);
create index if not exists fotos_activa_idx on public.fotos (activa, creado_en desc);

-- Normalmente ya existe: la crea `base-de-un-cliente.sql`. Se repite acá para
-- que este archivo se pueda correr solo en un cliente viejo, sin tener que
-- adivinar qué versión del esquema tiene.
create or replace function public.forzar_user_id()
returns trigger language plpgsql security definer set search_path = public as $$
begin new.user_id := auth.uid(); return new; end $$;

drop trigger if exists fotos_forzar_user on public.fotos;
create trigger fotos_forzar_user before insert on public.fotos
  for each row execute function public.forzar_user_id();

alter table public.fotos enable row level security;

-- El banco es del CLIENTE, no de cada persona: si lo sube la recepcionista
-- tiene que poder usarlo el que arma los posteos. Por eso se ve completo.
drop policy if exists "ver el banco" on public.fotos;
create policy "ver el banco" on public.fotos
  for select to authenticated using (true);

drop policy if exists "sumar al banco" on public.fotos;
create policy "sumar al banco" on public.fotos
  for insert to authenticated with check (auth.uid() = user_id);

-- Editar la descripción, las etiquetas o bajar una foto lo puede hacer
-- cualquiera del equipo. Borrar no: se desactiva, así una pieza vieja que la
-- usó no queda con un enlace roto.
drop policy if exists "editar el banco" on public.fotos;
create policy "editar el banco" on public.fotos
  for update to authenticated using (true) with check (true);

-- ── Cómo llega al worker lo que la persona eligió ─────────────────────────
--
-- El selector no puede mandar las fotos elegidas como adjuntos. Un adjunto es
-- un archivo suelto: llega sin `foco` y sin `quien`, que es exactamente lo que
-- el banco existe para conservar. Mandarlas así sería tirar el banco a la
-- basura en el último paso.
--
-- Va la CLAVE, que es con lo que el agente las nombra en su `fotos.json`.
alter table public.disenos
  add column if not exists fotos_elegidas text[] not null default '{}';

-- Las fotos del banco van a fotos/ del mismo bucket público.
drop policy if exists "subir al banco" on storage.objects;
create policy "subir al banco" on storage.objects
  for insert to authenticated
  with check (bucket_id = 'disenos' and (storage.foldername(name))[1] = 'fotos');
