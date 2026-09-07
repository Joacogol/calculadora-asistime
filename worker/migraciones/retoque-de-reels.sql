-- Retoque de reels: guardar lo que el motor armó, para poder corregirlo.
--
-- Hasta ahora el motor tiraba su propio trabajo. Un reel con subtítulos
-- automáticos resolvía veintidós frases con su segundo de entrada y de salida,
-- diez tramos recortados y un hook escrito — y todo eso vivía sólo en la
-- memoria del proceso mientras dibujaba el video. Al terminar quedaba el mp4 y
-- nada más.
--
-- El efecto era que **una frase mal transcrita no se podía corregir**. Había
-- que rehacer el reel entero, o sea volver a escuchar el audio, que da los
-- mismos errores otra vez, y de paso volver a tirar los aciertos.
--
-- Se corre en el SQL Editor de cada cliente. Es idempotente: se puede correr
-- de nuevo sin romper nada.

-- `armado`: el guion RESUELTO con el que se dibujó este reel.
--
-- No es un formato nuevo — es un guion válido, el mismo que entra por arriba,
-- pero con todo lo automático ya decidido. Devolvérselo al motor lo vuelve a
-- dibujar igual. Corregirle una frase y devolvérselo cambia esa frase y nada
-- más: los tiempos, los cortes y el resto del texto quedan idénticos.
alter table public.reels
  add column if not exists armado jsonb;

comment on column public.reels.armado is
  'El guion ya resuelto con el que se dibujó el reel: tramos con su entrada y '
  'salida, subtítulos con su segundo, hook escrito. Es un guion válido: '
  'devolvérselo al motor lo redibuja igual. Sirve para retocar sin volver a '
  'transcribir.';

-- `origen`: de qué reel salió éste, cuando es un retoque.
--
-- El retoque NO pisa el reel anterior: crea uno nuevo. Así se pueden comparar
-- los dos, y una corrección que salió peor no se lleva puesto el original.
alter table public.reels
  add column if not exists origen uuid;

comment on column public.reels.origen is
  'Si este reel es el retoque de otro, cuál. El retoque no pisa el original: '
  'crea una fila nueva, así se pueden comparar y una corrección que salió peor '
  'no se lleva puesto lo que ya estaba bien.';

-- Para poder pedir «los retoques de este reel» sin recorrer la tabla entera.
create index if not exists reels_origen_idx
  on public.reels (origen)
  where origen is not null;

-- Correcciones de transcripción que la marca ya aprendió.
--
-- Whisper escribe lo que oye, y con los nombres propios se equivoca siempre
-- igual: «Boss Padel» sale «vos panel» una y otra vez. Sin memoria, la misma
-- corrección hay que hacerla en cada reel.
--
-- `de` es lo que el sistema escribe mal y `a` lo que tiene que decir. Se
-- aplican después de transcribir, sobre el texto, y además se le pasan al
-- modelo como vocabulario ANTES de escuchar — que es lo que evita el error en
-- vez de taparlo.
create table if not exists public.correcciones (
  id          uuid primary key default gen_random_uuid(),
  creado_en   timestamptz not null default now(),
  de          text not null,
  a           text not null,
  quien       text,
  -- La misma corrección dos veces no aporta nada y haría ruido en la lista que
  -- se le muestra a la persona.
  constraint correcciones_de_unica unique (de)
);

comment on table public.correcciones is
  'Cómo se escribe cada palabra que la transcripción entiende mal. Se aplican '
  'a los subtítulos de todos los reels de esta marca.';

alter table public.correcciones enable row level security;

-- Igual que el resto de las tablas del motor: sólo entra el worker, con la
-- clave de servicio. El chat llega por la Edge Function, nunca directo.
drop policy if exists correcciones_sin_anon on public.correcciones;
create policy correcciones_sin_anon
  on public.correcciones
  for all
  to anon, authenticated
  using (false)
  with check (false);
