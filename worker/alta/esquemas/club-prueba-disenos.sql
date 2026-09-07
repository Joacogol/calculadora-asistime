-- Generado por herramientas/esquema-de-cliente.py — no editar a mano.
-- Cliente «club-prueba-disenos» en el esquema «club_prueba», bucket «disenos-club-prueba».
create schema if not exists club_prueba;
grant usage on schema club_prueba to anon, authenticated, service_role;
alter default privileges in schema club_prueba
  grant all on tables to anon, authenticated, service_role;


-- ═══ base-de-un-cliente.sql ═══
-- La base de un cliente nuevo: las cuatro tablas que tienen que existir ANTES
-- de `plantillas.sql`, `plantilla-pedidos.sql` y `motor-pedidos.sql`.
--
-- Se corre una vez, en el Supabase de ese cliente. Es re-corrible: si algo ya
-- está, no falla ni pisa datos.
--
-- De dónde salió este archivo: se reconstruyó leyendo la base viva de Clínica
-- Preventiva —que es el cliente de referencia— y se aplicó a Stadium. Después
-- se compararon las dos bases columna por columna, política por política y
-- trigger por trigger. Los nombres de los `check` pueden no coincidir con los
-- de Clínica: eso no lo ve nadie más que Postgres.
--
-- Los `on delete` de las claves foráneas NO son decoración. Si una persona se
-- borra de `auth.users` y sus filas la apuntan sin regla, el borrado FALLA:
-- Postgres no deja quedar una referencia colgada. Con `set null` la fila queda
-- sin dueño y la historia se conserva. `publicaciones` va con `cascade` porque
-- una publicación de un diseño que ya no existe no significa nada.
--
-- No hay columna de marca en ninguna tabla, a propósito: cada cliente tiene su
-- propio proyecto de Supabase, así que de qué marca es una fila está
-- determinado por dónde vive. Una columna `marca` sería una invitación a
-- juntar dos clientes en una base, que es exactamente lo que no queremos.


-- ═══ Los dos ayudantes de los triggers ═══════════════════════════════════
--
-- `forzar_user_id` es la razón por la que las políticas de abajo pueden
-- confiar en `user_id`: el cliente no lo manda, lo pone la base. Si lo mandara
-- él, podría mandar el de otro.

create or replace function club_prueba.tocar_actualizado() returns trigger
language plpgsql set search_path = club_prueba, pg_temp as $$
begin new.actualizado_en := now(); return new; end $$;

create or replace function club_prueba.forzar_user_id() returns trigger
language plpgsql security definer set search_path = club_prueba, pg_temp as $$
begin new.user_id := auth.uid(); return new; end $$;

-- Los dos de abajo hacen lo mismo que los dos de arriba y existen sólo porque
-- `disenos` es la tabla más vieja del sistema y se armó antes de que los
-- ayudantes fueran compartidos. Se dejan para que la base de un cliente nuevo
-- sea idéntica a la del cliente de referencia y las dos se puedan comparar.

create or replace function club_prueba.disenos_tocar_actualizado() returns trigger
language plpgsql set search_path = club_prueba, pg_temp as $$
begin new.actualizado_en := now(); return new; end $$;

create or replace function club_prueba.disenos_forzar_user_id() returns trigger
language plpgsql security definer set search_path = club_prueba as $$
begin new.user_id := auth.uid(); return new; end $$;


-- ═══ disenos — los pedidos de pieza ══════════════════════════════════════

create table if not exists club_prueba.disenos (
  id             uuid primary key default gen_random_uuid(),
  creado_en      timestamptz not null default now(),
  actualizado_en timestamptz not null default now(),
  user_id        uuid references auth.users(id) on delete set null,
  mensaje        text not null,          -- lo que pidió el cliente, tal cual
  formatos       text[] not null default '{post}',
  sede           text,
  quien          text,
  estado         text not null default 'pendiente',
  titulo         text,
  urls           text[] default '{}',    -- las piezas terminadas
  "copy"         text,
  -- El spec.json exacto con el que se dibujó la pieza. Sin esto, corregir un
  -- diseño es imposible: cada pedido de cambio lo rehace desde cero y sale
  -- otra pieza. Ver DESPLEGAR.md, 5/9/2026.
  spec           jsonb,
  -- El diseño que este pedido viene a corregir. Con esto puesto, el worker
  -- parte de SU spec y cambia sólo lo que se pide.
  corrige        uuid references club_prueba.disenos(id) on delete set null,
  mensaje_agente text,
  documentos     jsonb default '[]'::jsonb,
  videos         jsonb default '[]'::jsonb,
  adjuntos       jsonb default '[]'::jsonb,
  metricas       jsonb default '{}'::jsonb,
  fotos_elegidas text[] not null default '{}',
  logo_socio     text,
  notas          text,
  constraint disenos_estado_valido
    check (estado in ('pendiente','generando','listo','error'))
);

-- Columnas que se sumaron después del primer cliente. Van sueltas para que
-- este archivo sirva igual en una base recién creada que en una que ya venía.
alter table club_prueba.disenos add column if not exists documentos     jsonb default '[]'::jsonb;
alter table club_prueba.disenos add column if not exists videos         jsonb default '[]'::jsonb;
alter table club_prueba.disenos add column if not exists adjuntos       jsonb default '[]'::jsonb;
alter table club_prueba.disenos add column if not exists metricas       jsonb default '{}'::jsonb;
alter table club_prueba.disenos add column if not exists fotos_elegidas text[] not null default '{}';
alter table club_prueba.disenos add column if not exists logo_socio     text;
alter table club_prueba.disenos add column if not exists notas          text;

comment on table  club_prueba.disenos is
  'Pedidos de diseño de la app del cliente. El worker (Cloud Run) los lee con la service_role key y sube las piezas al bucket `disenos`.';
comment on column club_prueba.disenos."copy" is
  'Texto del posteo, listo para publicar. No lleva notas ni encabezados.';
comment on column club_prueba.disenos.notas is
  'Decisiones y supuestos del diseñador. Es para quien pidió la pieza: nunca se publica.';

create index if not exists disenos_estado_idx
  on club_prueba.disenos (estado, creado_en);
create index if not exists disenos_user_creado_idx
  on club_prueba.disenos (user_id, creado_en desc);

drop trigger if exists disenos_forzar_user on club_prueba.disenos;
create trigger disenos_forzar_user before insert on club_prueba.disenos
  for each row execute function club_prueba.disenos_forzar_user_id();

drop trigger if exists disenos_tocar on club_prueba.disenos;
create trigger disenos_tocar before update on club_prueba.disenos
  for each row execute function club_prueba.disenos_tocar_actualizado();

alter table club_prueba.disenos enable row level security;

-- Cada uno ve lo suyo y nada más. El worker no pasa por acá: entra con la
-- service_role key, que se saltea RLS.
drop policy if exists "ver lo propio" on club_prueba.disenos;
create policy "ver lo propio" on club_prueba.disenos
  for select to authenticated using (auth.uid() = user_id and public.es_de('club-prueba-disenos'));

drop policy if exists "crear lo propio" on club_prueba.disenos;
create policy "crear lo propio" on club_prueba.disenos
  for insert to authenticated with check (auth.uid() is not null and public.es_de('club-prueba-disenos'));

-- No hay política de update ni de delete, y es a propósito: un pedido ya hecho
-- no se edita. Si hay que cambiarlo, se pide otro.


-- ═══ fotos — el banco de imágenes del cliente ════════════════════════════

create table if not exists club_prueba.fotos (
  id          uuid primary key default gen_random_uuid(),
  creado_en   timestamptz not null default now(),
  user_id     uuid references auth.users(id) on delete set null,
  clave       text not null,          -- la ruta dentro del bucket
  url         text not null,
  descripcion text,                   -- qué se ve; es lo que lee el diseñador
  etiquetas   text[] not null default '{}',
  quien       jsonb  not null default '{}'::jsonb,
  foco        jsonb  not null default '{}'::jsonb,
  ancho       int,
  alto        int,
  activa      boolean not null default true
);

create unique index if not exists fotos_clave_idx on club_prueba.fotos (clave);
create index if not exists fotos_activa_idx on club_prueba.fotos (activa, creado_en desc);

drop trigger if exists fotos_forzar_user on club_prueba.fotos;
create trigger fotos_forzar_user before insert on club_prueba.fotos
  for each row execute function club_prueba.forzar_user_id();

alter table club_prueba.fotos enable row level security;

-- El banco es de la marca, no de quien subió cada foto: lo ve y lo edita
-- cualquiera del equipo. Sumar sí queda a nombre de uno.
drop policy if exists "ver el banco" on club_prueba.fotos;
create policy "ver el banco" on club_prueba.fotos
  for select to authenticated using (true);

drop policy if exists "sumar al banco" on club_prueba.fotos;
create policy "sumar al banco" on club_prueba.fotos
  for insert to authenticated with check (auth.uid() = user_id and public.es_de('club-prueba-disenos'));

drop policy if exists "editar el banco" on club_prueba.fotos;
create policy "editar el banco" on club_prueba.fotos
  for update to authenticated using (true) with check (true);


-- ═══ cuentas_ig — el token de Instagram ══════════════════════════════════

create table if not exists club_prueba.cuentas_ig (
  id          uuid primary key default gen_random_uuid(),
  creado_en   timestamptz not null default now(),
  usuario     text,
  ig_user_id  text,
  token       text not null,
  renovado_en timestamptz not null default now(),
  expira_en   timestamptz,
  activa      boolean not null default true,
  mensaje     text
);

alter table club_prueba.cuentas_ig enable row level security;

-- RLS prendido y NINGUNA política, a propósito. Acá vive un token que publica
-- en el Instagram del cliente: sin política, `authenticated` no lee ni una
-- fila. Sólo llega el worker, con la service_role key. Si alguna vez hay que
-- mostrar la cuenta conectada en la app, se agrega una política que devuelva
-- `usuario` y `activa` — nunca `token`.


-- La cara pública de `cuentas_ig`: todo menos el token. La consulta
-- `api-publicar` antes de encolar nada —sin cuenta conectada, la fila
-- quedaría esperando para siempre y el chat diría «ya sale»— y sirve para
-- mostrar en la app qué cuenta está conectada.
--
-- **Faltaba acá.** Existía a mano en Boss y en Clínica, así que Asistime la
-- descubrió el 3/9/2026 cuando publicar ya estaba armado: la función contesta
-- «esta marca no tiene Instagram conectado» y el motivo real es que la vista
-- no existe. Ahora el cliente que viene la recibe con la base.
--
-- `security_invoker` no es un detalle: sin él la vista corre con los permisos
-- de su dueño y se saltea el RLS de `cuentas_ig` —que no tiene políticas
-- justamente para que nadie la lea—, así que cualquiera con la clave `anon`
-- vería el usuario de Instagram del cliente y el vencimiento de su token.
create or replace view club_prueba.instagram_estado
with (security_invoker = on) as
  select usuario,
         activa,
         expira_en,
         (expira_en is not null and expira_en < now() + interval '7 days') as por_vencer,
         mensaje
    from club_prueba.cuentas_ig;

revoke all on club_prueba.instagram_estado from anon;
grant select on club_prueba.instagram_estado to authenticated, service_role;


-- ═══ publicaciones — la cola de posteo ═══════════════════════════════════

create table if not exists club_prueba.publicaciones (
  id             uuid primary key default gen_random_uuid(),
  creado_en      timestamptz not null default now(),
  actualizado_en timestamptz not null default now(),
  user_id        uuid references auth.users(id) on delete set null,
  diseno_id      uuid references club_prueba.disenos(id) on delete cascade,
  tipo           text not null default 'post',
  urls           text[] not null default '{}',
  caption        text,
  publicar_en    timestamptz not null default now(),
  estado         text not null default 'programado',
  contenedor     text,                -- el id del contenedor de Meta
  ig_id          text,
  permalink      text,
  mensaje        text,
  intentos       int not null default 0,
  esperas        int not null default 0,
  constraint publicaciones_tipo_valido
    check (tipo in ('post','carrusel','story','reel')),
  constraint publicaciones_estado_valido
    check (estado in ('programado','subiendo','publicado','error','cancelado'))
);

create index if not exists publicaciones_cola_idx
  on club_prueba.publicaciones (estado, publicar_en);
create index if not exists publicaciones_user_idx
  on club_prueba.publicaciones (user_id, creado_en desc);
create index if not exists publicaciones_diseno_idx
  on club_prueba.publicaciones (diseno_id);

drop trigger if exists publicaciones_forzar_user on club_prueba.publicaciones;
create trigger publicaciones_forzar_user before insert on club_prueba.publicaciones
  for each row execute function club_prueba.forzar_user_id();

drop trigger if exists publicaciones_tocar on club_prueba.publicaciones;
create trigger publicaciones_tocar before update on club_prueba.publicaciones
  for each row execute function club_prueba.tocar_actualizado();

alter table club_prueba.publicaciones enable row level security;

drop policy if exists "ver lo propio pub" on club_prueba.publicaciones;
create policy "ver lo propio pub" on club_prueba.publicaciones
  for select to authenticated using (auth.uid() = user_id and public.es_de('club-prueba-disenos'));

drop policy if exists "programar lo propio" on club_prueba.publicaciones;
create policy "programar lo propio" on club_prueba.publicaciones
  for insert to authenticated with check (auth.uid() = user_id and public.es_de('club-prueba-disenos'));

-- Se puede cambiar o cancelar mientras NO haya salido. `subiendo` queda afuera
-- de las dos listas: si el worker ya lo está mandando a Meta, editarlo desde
-- la app dejaría la fila diciendo una cosa y el posteo siendo otra.
drop policy if exists "cambiar lo no publicado" on club_prueba.publicaciones;
create policy "cambiar lo no publicado" on club_prueba.publicaciones
  for update to authenticated
  using       (auth.uid() = user_id and public.es_de('club-prueba-disenos') and estado in ('programado','error'))
  with check  (auth.uid() = user_id and public.es_de('club-prueba-disenos') and estado in ('programado','cancelado'));


-- ═══ El bucket `disenos` ═════════════════════════════════════════════════
--
-- Público de lectura porque Instagram tiene que poder bajarse la imagen por
-- URL para publicarla. Escribir es otra cosa: va por las políticas de abajo.

insert into storage.buckets (id, name, public)
values ('disenos-club-prueba', 'disenos-club-prueba', true)
on conflict (id) do update set public = true;

-- Tres carpetas y tres permisos distintos, en vez de "subir a donde sea":
--   fotos/    el banco de la marca — cualquiera del equipo
--   socios/   logos de terceros — cualquiera del equipo
--   adjuntos/<user_id>/  lo que manda una persona con su pedido — sólo suyo
-- El worker sube las piezas terminadas con la service_role key, que no pasa
-- por acá.
drop policy if exists "subir al banco · club_prueba" on storage.objects;
create policy "subir al banco · club_prueba" on storage.objects
  for insert to authenticated with check (
    bucket_id = 'disenos-club-prueba' and (storage.foldername(name))[1] = 'fotos');

drop policy if exists "subir logos de socios · club_prueba" on storage.objects;
create policy "subir logos de socios · club_prueba" on storage.objects
  for insert to authenticated with check (
    bucket_id = 'disenos-club-prueba' and (storage.foldername(name))[1] = 'socios');

drop policy if exists "subir mis adjuntos · club_prueba" on storage.objects;
create policy "subir mis adjuntos · club_prueba" on storage.objects
  for insert to authenticated with check (
    bucket_id = 'disenos-club-prueba'
    and (storage.foldername(name))[1] = 'adjuntos'
    and (storage.foldername(name))[2] = auth.uid()::text);


-- ═══ plantillas.sql ═══
-- Las plantillas de la marca, versionadas, en la base del cliente.
--
-- Se corre una vez en el Supabase de cada cliente, desde el SQL Editor.
--
-- Hasta acá una plantilla era un archivo del despliegue: corregirla o agregar
-- una era editar código, armar la imagen y esperar el build. Con la plantilla
-- acá, se guarda una versión nueva, se publica, y la pieza siguiente ya sale
-- con el cambio — el mismo camino que ya hace el manual de marca en Asistime.
--
-- No hay columna de marca, igual que en `disenos`: cada cliente tiene su base,
-- así que de qué marca es una plantilla está determinado por dónde vive.
--
-- El disco NO desaparece. Las plantillas que vienen en el despliegue siguen
-- siendo la red: si la base no contesta, el worker diseña con esas y el club
-- no se queda sin sus piezas del día porque una consulta tardó.

create table if not exists club_prueba.plantillas (
  id         bigserial primary key,
  plantilla  text        not null,   -- el slug: torneo, americano, socio…
  version    int         not null,
  etiqueta   text,                   -- qué cambió, en una línea
  html       text        not null,   -- el diseño, con {{ campos }}
  contrato   jsonb       not null,   -- formatos, medidas, campos y notas
  publicada  boolean     not null default false,
  creada_en  timestamptz not null default now(),
  quien      text,
  constraint plantilla_no_vacia check (length(trim(plantilla)) > 0),
  constraint version_positiva   check (version > 0),
  unique (plantilla, version)
);

-- Que existan dos versiones publicadas de la misma plantilla no es un error
-- que haya que acordarse de evitar: acá es imposible. Sin esto, el worker
-- levantaría dos filas para el mismo slug y cuál gana dependería del orden en
-- que vuelvan, que es la clase de bug que aparece una vez cada tres semanas.
create unique index if not exists plantillas_una_publicada
  on club_prueba.plantillas (plantilla) where publicada;

create index if not exists plantillas_publicadas_idx
  on club_prueba.plantillas (plantilla, version desc);


-- ── Guardar ───────────────────────────────────────────────────────────────
-- El número de versión lo calcula la base y no quien llama. Si lo calculara el
-- cliente —leer el máximo, sumar uno, escribir— dos guardados al mismo tiempo
-- pedirían la misma versión y uno de los dos se perdería contra el unique.

create or replace function club_prueba.guardar_plantilla(
  p_plantilla text,
  p_html      text,
  p_contrato  jsonb,
  p_etiqueta  text default null,
  p_quien     text default null,
  p_publicar  boolean default false
) returns club_prueba.plantillas
language plpgsql security definer set search_path = club_prueba, pg_temp as $$
declare
  v_version int;
  v_fila    club_prueba.plantillas;
begin
  select coalesce(max(version), 0) + 1 into v_version
    from club_prueba.plantillas where plantilla = p_plantilla;

  insert into club_prueba.plantillas (plantilla, version, etiqueta, html, contrato, quien)
  values (p_plantilla, v_version, p_etiqueta, p_html, p_contrato, p_quien)
  returning * into v_fila;

  if p_publicar then
    v_fila := club_prueba.publicar_plantilla(p_plantilla, v_version);
  end if;

  return v_fila;
end $$;


-- ── Publicar ──────────────────────────────────────────────────────────────
-- Despublicar la anterior y publicar la nueva son dos statements, pero una
-- sola transacción: no existe un instante en que la marca se quede sin esa
-- plantilla, ni uno en que tenga dos.

create or replace function club_prueba.publicar_plantilla(
  p_plantilla text,
  p_version   int
) returns club_prueba.plantillas
language plpgsql security definer set search_path = club_prueba, pg_temp as $$
declare v_fila club_prueba.plantillas;
begin
  update club_prueba.plantillas set publicada = false
    where plantilla = p_plantilla and publicada;

  update club_prueba.plantillas set publicada = true
    where plantilla = p_plantilla and version = p_version
    returning * into v_fila;

  if v_fila.id is null then
    raise exception 'no existe la versión % de la plantilla «%»',
      p_version, p_plantilla;
  end if;
  return v_fila;
end $$;


-- ── Quién puede qué ───────────────────────────────────────────────────────
-- El worker y el estudio escriben con la service_role key, que no pasa por
-- RLS. Para todo lo demás esto es de sólo lectura, y sólo lo publicado: un
-- borrador a medio hacer no tiene por qué verse desde la app del cliente.

alter table club_prueba.plantillas enable row level security;

drop policy if exists "ver lo publicado" on club_prueba.plantillas;
create policy "ver lo publicado" on club_prueba.plantillas
  for select to authenticated using (publicada);

-- Publicar una plantilla cambia todas las piezas que se hagan de ahí en
-- adelante. Eso pasa por el estudio, que sabe quién lo pidió y deja registro,
-- no por una llamada suelta desde el navegador de cualquiera.
-- Las dos funciones son SECURITY DEFINER: corren con los permisos de quien las
-- creó, no de quien las llama. Así que quién puede llamarlas es TODA la
-- seguridad que tienen.
--
-- Acá había un `revoke ... from anon, authenticated` que no hacía nada, y es
-- un error fácil de repetir: Postgres le da EXECUTE a PUBLIC en cada función
-- nueva, y `anon` y `authenticated` heredan de PUBLIC. Sacarles el permiso
-- directo —que nunca tuvieron— deja el heredado intacto.
--
-- El agujero era real: con la anon key, que vive en el código del navegador y
-- no es secreta, cualquiera podía llamar a `/rest/v1/rpc/guardar_plantilla`
-- con el HTML que quisiera y `p_publicar => true`. La pieza siguiente del
-- cliente salía con eso. `publicar_plantilla` sola alcanzaba para volver a
-- poner en vivo una versión vieja.
--
-- `service_role` tiene EXECUTE por un grant propio, así que el worker y las
-- Edge Functions no se enteran de esto.
revoke execute on function club_prueba.guardar_plantilla(text, text, jsonb, text, text, boolean)
  from public, anon, authenticated;
revoke execute on function club_prueba.publicar_plantilla(text, int)
  from public, anon, authenticated;


-- ═══ plantilla-pedidos.sql ═══
-- Los pedidos de plantilla nueva. Va después de `plantillas.sql`.
--
-- Mismo camino que `disenos`, otro objeto: alguien lo pide en castellano, el
-- worker lo atiende en la corrida siguiente, y lo que queda es un BORRADOR que
-- hay que mirar antes de publicar. Una plantilla se usa muchas veces: que se
-- ponga en uso sola sería cambiar todas las piezas futuras sin que nadie mire.
create table if not exists club_prueba.plantilla_pedidos (
  id             uuid primary key default gen_random_uuid(),
  creado_en      timestamptz not null default now(),
  actualizado_en timestamptz not null default now(),
  mensaje        text not null,
  quien          text,
  estado         text not null default 'pendiente',
  -- Si viene con el id de una plantilla que ya existe, el pedido es una
  -- CORRECCIÓN y no una plantilla nueva: el worker baja la versión publicada y
  -- la edita, en vez de escribir una de cero. Es la diferencia entre cuatro
  -- turnos y cuarenta, y sobre todo es la diferencia entre corregir la
  -- plantilla que la gente usa y reemplazarla por otra parecida.
  corrige        text,
  -- Las fotos que la persona mandó en el chat junto con el pedido: «poné
  -- como fondo esta». Mismo nombre y misma forma que en `disenos`
  -- —[{url, nombre}]— porque es el mismo objeto y lo copia el mismo código.
  -- Un segundo nombre para lo mismo es una manera de que dentro de seis meses
  -- alguien arregle uno y no el otro.
  adjuntos       jsonb not null default '[]'::jsonb,
  -- lo que sale
  plantilla      text,
  version        int,
  preview        text[] default '{}',
  notas          text,
  mensaje_agente text,
  metricas       jsonb default '{}'::jsonb,
  constraint pedido_estado_valido
    check (estado in ('pendiente','generando','listo','error')),
  constraint pedido_no_vacio check (length(trim(mensaje)) >= 10)
);

alter table club_prueba.plantilla_pedidos
  add column if not exists corrige text;

alter table club_prueba.plantilla_pedidos
  add column if not exists adjuntos jsonb not null default '[]'::jsonb;

create index if not exists plantilla_pedidos_estado_idx
  on club_prueba.plantilla_pedidos (estado, creado_en);

drop trigger if exists plantilla_pedidos_tocar on club_prueba.plantilla_pedidos;
create trigger plantilla_pedidos_tocar before update on club_prueba.plantilla_pedidos
  for each row execute function club_prueba.tocar_actualizado();

-- El worker escribe con la service_role key, que no pasa por RLS. Desde afuera
-- esto es de solo lectura: pedir una plantilla cambia todas las piezas futuras
-- y entra por la Edge Function, que verifica la clave.
alter table club_prueba.plantilla_pedidos enable row level security;

drop policy if exists "ver los pedidos" on club_prueba.plantilla_pedidos;
create policy "ver los pedidos" on club_prueba.plantilla_pedidos
  for select to authenticated using (true);


-- ═══ fotos-editadas.sql ═══
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

create table if not exists club_prueba.fotos_editadas (
  id             uuid primary key default gen_random_uuid(),
  creado_en      timestamptz not null default now(),
  actualizado_en timestamptz not null default now(),

  -- `on delete set null` y no nada: si una persona se borra de `auth.users`,
  -- sin regla el borrado FALLA. Los `on delete` de las claves foráneas no son
  -- decoración.
  user_id        uuid references auth.users(id) on delete set null,

  -- Qué se pidió. `verbo` es uno de los seis; `instruccion` es el texto libre
  -- que usan `crear`, `retoque` y `escena`.
  --
  -- `foto` admite NULL desde que existe `crear`, que no parte de ninguna: es el
  -- único verbo que inventa la imagen entera. Los otros cinco la exigen, y eso
  -- lo hace cumplir `api-fotos` antes de anotar la fila — la restricción vive
  -- donde se sabe qué verbo es, no en la columna, que no lo sabe.
  verbo          text not null,
  foto           text,
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
  on club_prueba.fotos_editadas (estado, creado_en);

create or replace function club_prueba.fotos_editadas_tocar() returns trigger
language plpgsql set search_path = club_prueba, pg_temp as $$
begin new.actualizado_en := now(); return new; end $$;

drop trigger if exists fotos_editadas_tocar on club_prueba.fotos_editadas;
create trigger fotos_editadas_tocar before update on club_prueba.fotos_editadas
  for each row execute function club_prueba.fotos_editadas_tocar();

drop trigger if exists fotos_editadas_forzar_user on club_prueba.fotos_editadas;
create trigger fotos_editadas_forzar_user before insert on club_prueba.fotos_editadas
  for each row execute function club_prueba.forzar_user_id();

-- RLS prendida y cada quien ve lo suyo, igual que los diseños.
alter table club_prueba.fotos_editadas enable row level security;

drop policy if exists "ver mis fotos editadas" on club_prueba.fotos_editadas;
create policy "ver mis fotos editadas" on club_prueba.fotos_editadas
  for select to authenticated using (user_id = auth.uid());

drop policy if exists "pedir una edición" on club_prueba.fotos_editadas;
create policy "pedir una edición" on club_prueba.fotos_editadas
  for insert to authenticated with check (true);


-- ═══ motor-pedidos.sql ═══
-- Los pedidos que necesitan tocar el motor de diseño. Va junto a las otras colas.
--
-- ## Por qué existe
--
-- Hasta que se agregó esto, `avisar_cambio_motor` mandaba un mail y nada más.
-- Un mail que nadie lee es un pedido perdido — y, más importante, no se puede
-- contar. Sin este registro no hay forma de saber si los cambios de motor pasan
-- dos veces por año o dos por semana, que es justo el dato que decide si vale
-- la pena automatizarlos.
--
-- Esa pregunta es real: el plantillero ya demuestra que un agente puede
-- escribir, dibujar, mirar y corregir. Hacerlo escribir el motor en vez de una
-- plantilla no es un salto conceptual; lo que cambia es cuánto se rompe si sale
-- mal. Antes de construir esa maquinaria conviene saber cuántas veces al año se
-- usaría.
--
-- Misma forma que `plantilla_pedidos` a propósito: quien entienda una entiende
-- la otra, y las dos se consultan igual.
create table if not exists club_prueba.motor_pedidos (
  id             uuid primary key default gen_random_uuid(),
  creado_en      timestamptz not null default now(),
  actualizado_en timestamptz not null default now(),
  -- lo que pidieron
  resumen        text not null,
  parte          text,
  quien          text,
  -- Qué pasó con el pedido. Arranca `anotado`. Si el motorista está prendido
  -- lo toma (`generando`) y deja una propuesta (`propuesto`) o se cae
  -- (`error`); de ahí en adelante lo mueve una persona: `en_curso` cuando
  -- alguien lo agarra, `hecho` cuando salió, `descartado` cuando se decidió
  -- que no va. Que exista `descartado` importa: un pedido que se decidió no
  -- hacer es información, y hoy se pierde.
  estado         text not null default 'anotado',
  nota           text,
  -- ── Lo que deja el motorista ────────────────────────────────────────────
  -- Una PROPUESTA, no un despliegue: el parche en formato diff, las imágenes
  -- que dibujó para mostrar que anda, y lo que quiera contar de lo que hizo.
  -- Nadie las aplica solo — para eso está `en_curso`, que lo pone una persona.
  parche         text,
  evidencia      jsonb,
  notas          text,
  metricas       jsonb default '{}'::jsonb,
  constraint motor_estado_valido
    check (estado in ('anotado','generando','propuesto',
                      'en_curso','hecho','descartado','error')),
  constraint motor_resumen_no_vacio check (length(trim(resumen)) >= 10)
);

-- Para una base que ya tenía la tabla de antes del motorista. Sin esto, el
-- motorista escribe en columnas que no existen y el pedido queda `generando`
-- para siempre — que fue exactamente lo que pasó la primera vez.
alter table club_prueba.motor_pedidos add column if not exists parche    text;
alter table club_prueba.motor_pedidos add column if not exists evidencia jsonb;
alter table club_prueba.motor_pedidos add column if not exists notas     text;
alter table club_prueba.motor_pedidos add column if not exists metricas  jsonb default '{}'::jsonb;

alter table club_prueba.motor_pedidos drop constraint if exists motor_estado_valido;
alter table club_prueba.motor_pedidos add  constraint motor_estado_valido
  check (estado in ('anotado','generando','propuesto',
                    'en_curso','hecho','descartado','error'));

create index if not exists motor_pedidos_estado_idx
  on club_prueba.motor_pedidos (estado, creado_en desc);

drop trigger if exists motor_pedidos_tocar on club_prueba.motor_pedidos;
create trigger motor_pedidos_tocar before update on club_prueba.motor_pedidos
  for each row execute function club_prueba.tocar_actualizado();

-- Igual que las otras colas: se escribe con la service_role, desde afuera es de
-- sólo lectura y la puerta es la Edge Function.
alter table club_prueba.motor_pedidos enable row level security;

drop policy if exists "ver los pedidos de motor" on club_prueba.motor_pedidos;
create policy "ver los pedidos de motor" on club_prueba.motor_pedidos
  for select to authenticated using (true);


-- ## Para leerlo después
--
-- Cuántos por mes, y en qué estado quedaron:
--
--   select date_trunc('month', creado_en) as mes, estado, count(*)
--     from club_prueba.motor_pedidos group by 1, 2 order by 1 desc, 2;
--
-- Y qué es lo que más piden, para ver si hay un patrón que se resuelva de una:
--
--   select parte, count(*) from club_prueba.motor_pedidos
--    group by 1 order by 2 desc;


-- ═══ cobro.sql ═══
-- El saldo y el consumo de un cliente.
--
-- Se corre UNA VEZ en el Supabase de cada cliente. Es aditivo: no toca nada de
-- lo que ya anda.
--
-- ── Por qué un libro de movimientos y no un campo `saldo` ─────────────────
--
-- La tentación es tener una columna `saldo` y sumarle o restarle. No hagas eso
-- con plata. Un campo mutable se desincroniza el día que una corrida se muere
-- entre generar la pieza y actualizar el número, y cuando se desincroniza no
-- hay forma de saber cuál era el valor correcto: perdiste la historia.
--
-- Acá cada movimiento es una FILA que no se modifica nunca, y el saldo es la
-- suma. Si algo sale mal, se ve exactamente qué pasó y cuándo. Es como lleva la
-- cuenta cualquier banco, y por el mismo motivo.
--
-- ── Qué ve el cliente y qué no ────────────────────────────────────────────
--
-- `movimientos` guarda las dos cifras: `monto_usd`, que es lo que se le cobra,
-- y `costo_usd`, que es lo que nos cuesta a nosotros la API. La segunda no la
-- puede ver: RLS sin política de select cierra la tabla entera, y el cliente
-- llega a sus datos por la vista `mi_cuenta`, que expone el total del mes y el
-- saldo — y nada más.
--
-- El multiplicador NO vive acá. Vive en la configuración del worker, en Google
-- Cloud. Un número que no está en la base del cliente es un número que no se
-- puede leer desde la base del cliente.

create table if not exists club_prueba.movimientos (
  id          uuid primary key default gen_random_uuid(),
  creado_en   timestamptz not null default now(),

  -- `abono`   el consumo que incluye el plan mensual, cargado al facturar
  -- `carga`   una recarga que pagó el cliente
  -- `consumo` una pieza generada (va en negativo)
  -- `ajuste`  una corrección a mano, con el motivo en `detalle`
  tipo        text not null check (tipo in ('abono','carga','consumo','ajuste')),

  -- Positivo suma al saldo, negativo resta. El consumo SIEMPRE es negativo.
  monto_usd   numeric(12,4) not null,

  -- Lo que nos costó a nosotros. Sólo en `consumo`. **Nunca sale de acá.**
  costo_usd   numeric(12,6),

  diseno_id   uuid references club_prueba.disenos(id) on delete set null,
  detalle     text
);

create index if not exists movimientos_fecha_idx
  on club_prueba.movimientos (creado_en desc);
create index if not exists movimientos_tipo_idx
  on club_prueba.movimientos (tipo, creado_en desc);

alter table club_prueba.movimientos enable row level security;

-- Sin políticas: nadie entra con la clave del navegador. El worker usa la
-- service_role key, que no pasa por RLS. Ver el mismo patrón en `cuentas_ig`.


-- ── Lo que el cliente sí puede ver ────────────────────────────────────────
--
-- `security_invoker = off` hace que la vista corra con los permisos de quien la
-- creó y no de quien la consulta: es una ventana angosta a una tabla cerrada.
-- Devuelve una sola fila, sin desglose por pieza y sin el costo.
create or replace view club_prueba.mi_cuenta
with (security_invoker = off) as
select
  coalesce(sum(monto_usd), 0)::numeric(12,2) as saldo_usd,
  coalesce(sum(monto_usd) filter (
    where tipo = 'consumo'
      and creado_en >= date_trunc('month', now())), 0)::numeric(12,2) * -1
      as consumido_mes_usd,
  coalesce(count(*) filter (
    where tipo = 'consumo'
      and creado_en >= date_trunc('month', now())), 0) as piezas_mes,
  (select max(creado_en) from club_prueba.movimientos where tipo = 'carga')
      as ultima_carga
from club_prueba.movimientos;

grant select on club_prueba.mi_cuenta to authenticated;


-- ── El aviso de saldo bajo ────────────────────────────────────────────────
--
-- Que el cliente se entere ANTES de que un pedido le vuelva rechazado. Un
-- diseño que no sale porque se acabó el saldo, sin aviso previo, se lee como
-- que el sistema falló — y esa es la peor forma de pedirle plata a alguien.
create or replace view club_prueba.estado_saldo
with (security_invoker = off) as
select
  saldo_usd,
  consumido_mes_usd,
  piezas_mes,
  case
    when saldo_usd <= 0    then 'agotado'
    when saldo_usd < 5     then 'critico'
    when saldo_usd < 15    then 'bajo'
    else 'ok'
  end as estado,
  case
    when saldo_usd <= 0 then
      'Se agotó el saldo. Recargá para seguir generando diseños.'
    when saldo_usd < 5 then
      'Te queda poco saldo: alcanza para unos pocos diseños más.'
    when saldo_usd < 15 then
      'Saldo bajo. Conviene recargar en los próximos días.'
    else ''
  end as mensaje
from club_prueba.mi_cuenta;

grant select on club_prueba.estado_saldo to authenticated;


-- Los `grant` que Supabase pone por defecto en cualquier tabla nueva de
-- `public`. RLS sin políticas ya bloquea todo, pero esto es la segunda cerradura:
-- si alguna vez alguien agrega una política de select «para probar algo», el
-- grant revocado sigue tapando el agujero.
revoke all on club_prueba.movimientos from anon, authenticated;

