-- Ducart registra costos sin exigir ni descontar saldo (alta autorizada).
-- El motor y api-disenos reconocen el modo sin prepago por ausencia de mi_cuenta.
-- Conservamos el libro movimientos y las vistas para auditoría interna: no se
-- agregan recargas ficticias, no se borra historia y no se altera otra marca.
do $$ begin
  if to_regclass('ducart.mi_cuenta') is not null then
    alter view ducart.mi_cuenta rename to cuenta_interna;
  end if;
  if to_regclass('ducart.estado_saldo') is not null then
    alter view ducart.estado_saldo rename to estado_prepago_interno;
  end if;
end $$;
revoke all on ducart.cuenta_interna, ducart.estado_prepago_interno from public, anon, authenticated;
grant select on ducart.cuenta_interna, ducart.estado_prepago_interno to service_role;
update public.clientes set cobra=false where marca='ducart-disenos';
notify pgrst, 'reload schema';
