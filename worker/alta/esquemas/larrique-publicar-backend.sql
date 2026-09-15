-- Permite al backend publicar las plantillas autorizadas de Larrique.
-- No concede acceso a anon, authenticated ni PUBLIC.
begin;
grant execute on function larrique.guardar_plantilla(text,text,jsonb,text,text,boolean) to service_role;
grant execute on function larrique.publicar_plantilla(text,integer) to service_role;
do $$
begin
 if not has_function_privilege('service_role','larrique.guardar_plantilla(text,text,jsonb,text,text,boolean)','EXECUTE')
 or not has_function_privilege('service_role','larrique.publicar_plantilla(text,integer)','EXECUTE') then
  raise exception 'No se habilitó publicación al backend';
 end if;
 if has_function_privilege('anon','larrique.guardar_plantilla(text,text,jsonb,text,text,boolean)','EXECUTE')
 or has_function_privilege('authenticated','larrique.guardar_plantilla(text,text,jsonb,text,text,boolean)','EXECUTE') then
  raise exception 'Revisar: la publicación no debe estar disponible a usuarios públicos';
 end if;
end $$;
commit;
