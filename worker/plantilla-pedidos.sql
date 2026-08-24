-- Los pedidos de plantilla nueva. Va después de `plantillas.sql`.
--
-- Mismo camino que `disenos`, otro objeto: alguien lo pide en castellano, el
-- worker lo atiende en la corrida siguiente, y lo que queda es un BORRADOR que
-- hay que mirar antes de publicar. Una plantilla se usa muchas veces: que se
-- ponga en uso sola sería cambiar todas las piezas futuras sin que nadie mire.
create table if not exists public.plantilla_pedidos (
  id             uuid primary key default gen_random_uuid(),
  creado_en      timestamptz not null default now(),
  actualizado_en timestamptz not null default now(),
  mensaje        text not null,
  quien          text,
  estado         text not null default 'pendiente',
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

create index if not exists plantilla_pedidos_estado_idx
  on public.plantilla_pedidos (estado, creado_en);

drop trigger if exists plantilla_pedidos_tocar on public.plantilla_pedidos;
create trigger plantilla_pedidos_tocar before update on public.plantilla_pedidos
  for each row execute function public.tocar_actualizado();

-- El worker escribe con la service_role key, que no pasa por RLS. Desde afuera
-- esto es de solo lectura: pedir una plantilla cambia todas las piezas futuras
-- y entra por la Edge Function, que verifica la clave.
alter table public.plantilla_pedidos enable row level security;

drop policy if exists "ver los pedidos" on public.plantilla_pedidos;
create policy "ver los pedidos" on public.plantilla_pedidos
  for select to authenticated using (true);
