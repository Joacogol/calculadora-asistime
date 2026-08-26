-- La cola de ediciones de foto, hermana de `reels`.
--
-- Mismo camino que un diseño y que un reel: el agente anota la fila y contesta
-- al instante, el worker la levanta y la trabaja. Acá la razón para NO esperar
-- adentro de la tool es más floja que en video —una edición tarda segundos, no
-- minutos— y aun así conviene, por dos motivos:
--
--   · la clave de Magnific vive en UN solo lugar, el worker, con sus topes de
--     créditos al lado. Ponerla también en las Edge Functions sería una segunda
--     copia de la llave que puede gastar toda la cuenta.
--   · el resultado de Magnific caduca: la URL de quitar fondo vive CINCO
--     minutos. Alguien tiene que bajarla y subirla al bucket enseguida, y ese
--     alguien ya existe.
--
-- Los estados son los mismos de siempre y por las mismas razones:
--
--     pendiente  → recién anotado por el agente
--     trabajando → se pidió a Magnific; `tarea` tiene el id cuando es asíncrono
--     listo      → el archivo está en el bucket, `url` lo apunta
--     rechazado  → sale más caro que el tope; NO se pidió
--     error      → algo falló; `notas` dice qué

create table if not exists public.fotos_editadas (
  id             uuid primary key default gen_random_uuid(),
  creado_en      timestamptz not null default now(),
  actualizado_en timestamptz not null default now(),

  -- `on delete set null` y no nada: si una persona se borra de `auth.users`,
  -- sin regla el borrado FALLA. Los `on delete` de las claves foráneas no son
  -- decoración.
  user_id        uuid references auth.users(id) on delete set null,

  -- Qué se pidió. `verbo` es uno de los cinco; `instruccion` es el texto libre
  -- que sólo usan `retoque` y `escena`.
  verbo          text not null,
  foto           text not null,
  instruccion    text,
  formato        text,          -- para `formato`: post, vert, story, reel

  estado         text not null default 'pendiente',
  modelo         text,
  tarea          text,
  url            text,          -- el resultado, ya en nuestro bucket
  quien          text,
  notas          text,
  creditos_estimados int,
  creditos_gastados  int,
  metricas       jsonb default '{}'::jsonb
);

-- Buscar la cola por estado es lo que hace el worker cada minuto, y buscar por
-- fecha es lo que hace el tope por hora. Sin el índice son dos escaneos de
-- tabla por minuto para siempre.
create index if not exists fotos_editadas_cola
  on public.fotos_editadas (estado, creado_en);

create or replace function public.fotos_editadas_tocar() returns trigger
language plpgsql set search_path = public, pg_temp as $$
begin new.actualizado_en := now(); return new; end $$;

drop trigger if exists fotos_editadas_tocar on public.fotos_editadas;
create trigger fotos_editadas_tocar before update on public.fotos_editadas
  for each row execute function public.fotos_editadas_tocar();

drop trigger if exists fotos_editadas_forzar_user on public.fotos_editadas;
create trigger fotos_editadas_forzar_user before insert on public.fotos_editadas
  for each row execute function public.forzar_user_id();

-- RLS prendida y cada quien ve lo suyo, igual que los diseños.
alter table public.fotos_editadas enable row level security;

drop policy if exists "ver mis fotos editadas" on public.fotos_editadas;
create policy "ver mis fotos editadas" on public.fotos_editadas
  for select to authenticated using (user_id = auth.uid());

drop policy if exists "pedir una edición" on public.fotos_editadas;
create policy "pedir una edición" on public.fotos_editadas
  for insert to authenticated with check (true);
