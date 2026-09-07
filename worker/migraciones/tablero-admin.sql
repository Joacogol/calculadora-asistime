-- ═══════════════════════════════════════════════════════════════════════
-- El libro central: lo que le cuesta a Asistime cada pieza de cada cliente
-- y lo que se le cobró. Va en el Supabase de Asistime (la casa), NUNCA en el
-- de un cliente: el cliente no tiene por qué ver los costos de los demás ni
-- el margen.
--
-- Lo escribe el worker (service_role, saltea RLS). Lo lee el tablero con un
-- usuario logueado cuyo email esté en `administradores`. El anon no ve nada.
--
-- Aplicado en qxjvtxumkljsroukpkny el 7/9/2026. Ver TABLERO-ADMIN.md.
-- ═══════════════════════════════════════════════════════════════════════

create extension if not exists pgcrypto;

-- ── Quién puede mirar ───────────────────────────────────────────────────
create table if not exists public.administradores (
  email      text primary key,
  creado_en  timestamptz not null default now()
);
insert into public.administradores (email) values ('joaquin@asistime.ai')
  on conflict do nothing;

create or replace function public.es_admin() returns boolean
language sql stable security definer set search_path = public as $$
  select exists (
    select 1 from public.administradores a
    where lower(a.email) = lower(coalesce(auth.jwt() ->> 'email', ''))
  );
$$;
revoke all on function public.es_admin() from public;
grant execute on function public.es_admin() to anon, authenticated, service_role;

-- ── Los clientes y su configuración comercial ───────────────────────────
-- Reemplaza la variable de entorno MARGEN. El worker la lee al arrancar
-- cada ciclo y cae al entorno si no puede leerla.
create table if not exists public.clientes (
  marca               text primary key,
  nombre              text not null,
  supabase_ref        text,
  margen              numeric(6,3) not null default 2.0 check (margen >= 1),
  cobra               boolean not null default true,
  moneda_factura      text not null default 'USD' check (moneda_factura in ('USD','UYU')),
  tope_usd_mes        numeric(12,2),
  -- De quién es la cuenta de Magnific con la que se gastan los créditos.
  -- Hoy hay UNA clave (MAGNIFIC_CLAVE) para todo el worker: es de Asistime.
  cuenta_creditos     text not null default 'asistime' check (cuenta_creditos in ('asistime','cliente')),
  -- Cuánto le cuesta a Asistime un crédito de Magnific. Null = todavía no
  -- se cargó: los créditos se muestran pero no se convierten a dólares.
  precio_credito_usd  numeric(10,6),
  activo              boolean not null default true,
  -- {logo, tinta, fondo, acento, secundario, fuente}: para vestir la
  -- pantalla del cliente con su identidad.
  identidad           jsonb not null default '{}'::jsonb,
  notas               text,
  creado_en           timestamptz not null default now(),
  actualizado_en      timestamptz not null default now()
);

create or replace function public.tocar_actualizado() returns trigger
language plpgsql as $$
begin
  new.actualizado_en := now();
  return new;
end $$;
drop trigger if exists clientes_tocar on public.clientes;
create trigger clientes_tocar before update on public.clientes
  for each row execute function public.tocar_actualizado();

-- ── El libro: una fila por cosa que costó plata ─────────────────────────
create table if not exists public.libro (
  id               uuid primary key default gen_random_uuid(),
  creado_en        timestamptz not null default now(),   -- cuándo se hizo la pieza
  anotado_en       timestamptz not null default now(),   -- cuándo entró al libro
  marca            text not null references public.clientes(marca),
  tipo             text not null check (tipo in ('placa','reel','video','foto','publicacion')),
  pieza_id         uuid not null,
  proveedor        text,               -- anthropic | fal | magnific | instagram | motor
  modelo           text,
  costo_usd        numeric(12,6) not null default 0,   -- lo que pagó Asistime
  creditos         integer not null default 0,         -- créditos de Magnific
  cuenta_creditos  text,
  segundos         numeric(10,2),
  tokens_entrada   bigint,
  tokens_salida    bigint,
  cache_lectura    bigint,
  cache_escritura  bigint,
  precio_usd       numeric(12,2) not null default 0,   -- lo que se le cobró
  margen_aplicado  numeric(6,3),
  cobrado_en       uuid,               -- movimientos.id en la base del cliente
  titulo           text,
  detalle          text,
  url              text,
  plantilla        text,
  avisos           jsonb,
  extra            jsonb not null default '{}'::jsonb,
  unique (marca, tipo, pieza_id)
);
create index if not exists libro_marca_mes on public.libro (marca, creado_en desc);

-- ── Cargas de saldo, anotadas desde el tablero ──────────────────────────
-- El tablero no tiene la clave de ningún cliente: anota acá y el worker,
-- que sí la tiene, copia la fila al `movimientos` del cliente en el
-- siguiente ciclo y marca `espejado_en`. Hasta entonces el saldo que ve el
-- cliente no la incluye.
create table if not exists public.cargas (
  id           uuid primary key default gen_random_uuid(),
  creado_en    timestamptz not null default now(),
  marca        text not null references public.clientes(marca),
  tipo         text not null check (tipo in ('carga','abono','ajuste')),
  monto_usd    numeric(12,2) not null,
  detalle      text,
  quien        text,
  espejado_en  timestamptz,
  espejo_id    uuid,                 -- movimientos.id del lado del cliente
  error        text
);

-- ── Lo que no es por pieza ──────────────────────────────────────────────
create table if not exists public.infraestructura (
  id         uuid primary key default gen_random_uuid(),
  mes        date not null,           -- siempre el día 1
  concepto   text not null,           -- Cloud Run, Supabase, Anthropic factura, …
  proveedor  text,
  monto_usd  numeric(12,2) not null,
  notas      text,
  creado_en  timestamptz not null default now()
);

-- ── Cierres mensuales ───────────────────────────────────────────────────
create table if not exists public.cierres (
  id             uuid primary key default gen_random_uuid(),
  marca          text not null references public.clientes(marca),
  mes            date not null,
  costo_usd      numeric(12,2) not null default 0,
  consumo_usd    numeric(12,2) not null default 0,   -- lo cobrado
  cargas_usd     numeric(12,2) not null default 0,
  infra_usd      numeric(12,2) not null default 0,
  saldo_usd      numeric(12,2) not null default 0,
  facturado      numeric(12,2),
  moneda         text not null default 'USD',
  tipo_cambio    numeric(12,4),
  notas          text,
  cerrado_en     timestamptz not null default now(),
  unique (marca, mes)
);

-- ── Latido del worker, para la pantalla de salud ────────────────────────
create table if not exists public.latidos (
  marca         text primary key,
  ultimo_ciclo  timestamptz not null default now(),
  pendientes    integer not null default 0,
  errores       integer not null default 0,
  version       text,
  detalle       jsonb not null default '{}'::jsonb
);

-- ── Vistas ──────────────────────────────────────────────────────────────
-- `security_invoker`: la vista corre con los permisos de quien la consulta,
-- así que RLS de las tablas de abajo sigue mandando.

create or replace view public.libro_mes with (security_invoker = true) as
select marca,
       date_trunc('month', creado_en)::date as mes,
       tipo,
       count(*)                                    as piezas,
       count(*) filter (where precio_usd > 0)      as cobradas,
       sum(costo_usd)::numeric(12,4)               as costo_usd,
       sum(precio_usd)::numeric(12,2)              as precio_usd,
       sum(creditos)                               as creditos,
       sum(coalesce(segundos, 0))::numeric(12,1)   as segundos
from public.libro
group by 1, 2, 3;

create or replace view public.infra_mes with (security_invoker = true) as
with seg as (
  select marca, date_trunc('month', creado_en)::date as mes,
         sum(coalesce(segundos, 0)) as segundos
  from public.libro group by 1, 2
), tot as (
  select mes, sum(segundos) as total from seg group by 1
), inf as (
  select mes, sum(monto_usd) as monto from public.infraestructura group by 1
)
select s.marca, s.mes, s.segundos::numeric(12,1) as segundos,
       t.total::numeric(12,1) as segundos_total,
       coalesce(i.monto, 0)::numeric(12,2) as infra_total_usd,
       case when t.total > 0
            then round(coalesce(i.monto, 0) * s.segundos / t.total, 4)
            else 0 end::numeric(12,4) as infra_usd
from seg s
join tot t using (mes)
left join inf i using (mes);

create or replace view public.saldos with (security_invoker = true) as
select c.marca, c.nombre, c.cobra, c.activo, c.margen,
       coalesce(k.cargas, 0)::numeric(12,2)                       as cargas_usd,
       coalesce(l.consumo, 0)::numeric(12,2)                      as consumo_usd,
       (coalesce(k.cargas, 0) - coalesce(l.consumo, 0))::numeric(12,2) as saldo_usd,
       coalesce(l.costo, 0)::numeric(12,4)                        as costo_usd,
       l.ultimo_consumo,
       k.ultima_carga,
       (select count(*) from public.cargas x
         where x.marca = c.marca and x.espejado_en is null and x.error is null) as cargas_sin_espejar
from public.clientes c
left join (select marca, sum(monto_usd) as cargas, max(creado_en) as ultima_carga
           from public.cargas group by 1) k on k.marca = c.marca
left join (select marca, sum(precio_usd) as consumo, sum(costo_usd) as costo,
                  max(creado_en) as ultimo_consumo
           from public.libro group by 1) l on l.marca = c.marca;

-- ── RLS: el worker (service_role) pasa; un admin logueado lee y escribe;
--    el anon no ve nada. ───────────────────────────────────────────────
do $$
declare t text;
begin
  foreach t in array array['administradores','clientes','libro','cargas',
                           'infraestructura','cierres','latidos'] loop
    execute format('alter table public.%I enable row level security', t);
    execute format('drop policy if exists "admin" on public.%I', t);
    execute format('create policy "admin" on public.%I for all to authenticated
                    using (public.es_admin()) with check (public.es_admin())', t);
  end loop;
end $$;

-- ── Los cuatro que hay hoy ──────────────────────────────────────────────
insert into public.clientes (marca, nombre, supabase_ref, cobra, notas) values
  ('boss-padel-disenos',         'Boss Padel',          'ndulchsiqutxibiwzzlc', true,  null),
  ('clinica-preventiva-disenos', 'Clínica Preventiva',  'jejohzzxxnhktdxpdqpy', true,  null),
  ('stadium-disenos',            'Stadium',             'heajbidxysjxxegqemka', true,  'sin cobro.sql todavía: el worker no le corta por saldo'),
  ('asistime-disenos',           'Asistime',            'qxjvtxumkljsroukpkny', false, 'la casa: se anota el costo, no se cobra')
on conflict (marca) do nothing;

