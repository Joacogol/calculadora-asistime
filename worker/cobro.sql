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

create table if not exists public.movimientos (
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

  diseno_id   uuid references public.disenos(id) on delete set null,
  detalle     text
);

create index if not exists movimientos_fecha_idx
  on public.movimientos (creado_en desc);
create index if not exists movimientos_tipo_idx
  on public.movimientos (tipo, creado_en desc);

alter table public.movimientos enable row level security;

-- Sin políticas: nadie entra con la clave del navegador. El worker usa la
-- service_role key, que no pasa por RLS. Ver el mismo patrón en `cuentas_ig`.


-- ── Lo que el cliente sí puede ver ────────────────────────────────────────
--
-- `security_invoker = off` hace que la vista corra con los permisos de quien la
-- creó y no de quien la consulta: es una ventana angosta a una tabla cerrada.
-- Devuelve una sola fila, sin desglose por pieza y sin el costo.
create or replace view public.mi_cuenta
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
  (select max(creado_en) from public.movimientos where tipo = 'carga')
      as ultima_carga
from public.movimientos;

grant select on public.mi_cuenta to authenticated;


-- ── El aviso de saldo bajo ────────────────────────────────────────────────
--
-- Que el cliente se entere ANTES de que un pedido le vuelva rechazado. Un
-- diseño que no sale porque se acabó el saldo, sin aviso previo, se lee como
-- que el sistema falló — y esa es la peor forma de pedirle plata a alguien.
create or replace view public.estado_saldo
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
from public.mi_cuenta;

grant select on public.estado_saldo to authenticated;


-- Los `grant` que Supabase pone por defecto en cualquier tabla nueva de
-- `public`. RLS sin políticas ya bloquea todo, pero esto es la segunda cerradura:
-- si alguna vez alguien agrega una política de select «para probar algo», el
-- grant revocado sigue tapando el agujero.
revoke all on public.movimientos from anon, authenticated;
