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
create table if not exists public.motor_pedidos (
  id             uuid primary key default gen_random_uuid(),
  creado_en      timestamptz not null default now(),
  actualizado_en timestamptz not null default now(),
  -- lo que pidieron
  resumen        text not null,
  parte          text,
  quien          text,
  -- Qué pasó con el pedido. Arranca `anotado` y lo mueve una persona:
  -- `en_curso` cuando alguien lo agarra, `hecho` cuando salió, `descartado`
  -- cuando se decidió que no va. Que exista `descartado` importa: un pedido que
  -- se decidió no hacer es información, y hoy se pierde.
  estado         text not null default 'anotado',
  nota           text,
  constraint motor_estado_valido
    check (estado in ('anotado','en_curso','hecho','descartado')),
  constraint motor_resumen_no_vacio check (length(trim(resumen)) >= 10)
);

create index if not exists motor_pedidos_estado_idx
  on public.motor_pedidos (estado, creado_en desc);

drop trigger if exists motor_pedidos_tocar on public.motor_pedidos;
create trigger motor_pedidos_tocar before update on public.motor_pedidos
  for each row execute function public.tocar_actualizado();

-- Igual que las otras colas: se escribe con la service_role, desde afuera es de
-- sólo lectura y la puerta es la Edge Function.
alter table public.motor_pedidos enable row level security;

drop policy if exists "ver los pedidos de motor" on public.motor_pedidos;
create policy "ver los pedidos de motor" on public.motor_pedidos
  for select to authenticated using (true);


-- ## Para leerlo después
--
-- Cuántos por mes, y en qué estado quedaron:
--
--   select date_trunc('month', creado_en) as mes, estado, count(*)
--     from public.motor_pedidos group by 1, 2 order by 1 desc, 2;
--
-- Y qué es lo que más piden, para ver si hay un patrón que se resuelva de una:
--
--   select parte, count(*) from public.motor_pedidos
--    group by 1 order by 2 desc;
