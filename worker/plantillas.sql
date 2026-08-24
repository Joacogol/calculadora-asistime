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

create table if not exists public.plantillas (
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
  on public.plantillas (plantilla) where publicada;

create index if not exists plantillas_publicadas_idx
  on public.plantillas (plantilla, version desc);


-- ── Guardar ───────────────────────────────────────────────────────────────
-- El número de versión lo calcula la base y no quien llama. Si lo calculara el
-- cliente —leer el máximo, sumar uno, escribir— dos guardados al mismo tiempo
-- pedirían la misma versión y uno de los dos se perdería contra el unique.

create or replace function public.guardar_plantilla(
  p_plantilla text,
  p_html      text,
  p_contrato  jsonb,
  p_etiqueta  text default null,
  p_quien     text default null,
  p_publicar  boolean default false
) returns public.plantillas
language plpgsql security definer set search_path = public, pg_temp as $$
declare
  v_version int;
  v_fila    public.plantillas;
begin
  select coalesce(max(version), 0) + 1 into v_version
    from public.plantillas where plantilla = p_plantilla;

  insert into public.plantillas (plantilla, version, etiqueta, html, contrato, quien)
  values (p_plantilla, v_version, p_etiqueta, p_html, p_contrato, p_quien)
  returning * into v_fila;

  if p_publicar then
    v_fila := public.publicar_plantilla(p_plantilla, v_version);
  end if;

  return v_fila;
end $$;


-- ── Publicar ──────────────────────────────────────────────────────────────
-- Despublicar la anterior y publicar la nueva son dos statements, pero una
-- sola transacción: no existe un instante en que la marca se quede sin esa
-- plantilla, ni uno en que tenga dos.

create or replace function public.publicar_plantilla(
  p_plantilla text,
  p_version   int
) returns public.plantillas
language plpgsql security definer set search_path = public, pg_temp as $$
declare v_fila public.plantillas;
begin
  update public.plantillas set publicada = false
    where plantilla = p_plantilla and publicada;

  update public.plantillas set publicada = true
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

alter table public.plantillas enable row level security;

drop policy if exists "ver lo publicado" on public.plantillas;
create policy "ver lo publicado" on public.plantillas
  for select to authenticated using (publicada);

-- Publicar una plantilla cambia todas las piezas que se hagan de ahí en
-- adelante. Eso pasa por el estudio, que sabe quién lo pidió y deja registro,
-- no por una llamada suelta desde el navegador de cualquiera.
revoke execute on function public.guardar_plantilla(text, text, jsonb, text, text, boolean)
  from anon, authenticated;
revoke execute on function public.publicar_plantilla(text, int)
  from anon, authenticated;
