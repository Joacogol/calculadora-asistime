-- Permisos del backend de Ducart. Ningún permiso nuevo para anon/authenticated.
grant execute on all functions in schema ducart to service_role;
grant usage, select on all sequences in schema ducart to service_role;
