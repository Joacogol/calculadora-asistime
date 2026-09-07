# Un solo Supabase para todos los clientes

Desde el 7/9/2026 un cliente nuevo **no lleva proyecto propio**: entra en el
Supabase de la casa (`qxjvtxumkljsroukpkny`) con su propio esquema de Postgres.

## Por qué

Los cuatro clientes que tenían proyecto propio suman 52 MB de base y 851 MB de
archivos. Un proyecto por cliente no se paga por los datos: se paga por tener
el contenedor prendido. Y multiplica el despliegue — cinco funciones de borde
por proyecto, veinte en total — que es exactamente cómo tres clientes quedaron
con la función de correcciones vieja sin que nadie se enterara.

Lo que NO se hizo, y a propósito: una sola tabla con una columna «cliente». Eso
traslada la separación al código, y el día que una consulta se olvida el filtro
un cliente ve las piezas de otro. Con un esquema por cliente la separación la
hace Postgres, el SQL de cada tabla es el mismo de siempre y entregarle a un
cliente todo lo suyo sigue siendo un comando: `pg_dump -n <esquema>`.

## Cómo se conecta cada uno

PostgREST elige el esquema por cabecera: `Accept-Profile` al leer y
`Content-Profile` al escribir. En el worker es el campo `esquema` del registro
(`app/registro.py`), que `Cliente` convierte en esas dos cabeceras
(`app/supa.py`). Un cliente sin `esquema` sigue hablando con `public`: por eso
los cuatro que tienen proyecto propio no se tocan.

## La puerta que sólo existe compartiendo proyecto

Con un proyecto por cliente, «cualquiera logueado puede encargar un diseño» era
seguro: los únicos usuarios de ese proyecto eran los de ese cliente.
Compartiendo proyecto, todos viven en el mismo `auth.users`, y esa misma
política deja que el usuario de un cliente encargue piezas —y gaste plata— en
la base de otro.

Por eso cada política de cada esquema exige además `public.es_de('<marca>')`,
que mira la tabla `public.membresias`. El worker y las funciones de borde entran
con la `service_role`, que se saltea RLS: esto es la puerta de las personas.

**Al dar de alta a alguien hay que anotarlo en `membresias`.** Un usuario que no
esté ahí puede entrar a la app y no va a poder pedir nada, con un error de
permisos que no dice por qué.

## El alta, paso a paso

```bash
# 1. El SQL del cliente, generado y versionado
python3 herramientas/esquema-de-cliente.py club-x-disenos > alta/esquemas/club-x-disenos.sql
git add alta/esquemas/club-x-disenos.sql && git commit -m "Alta de Club X" && git push
git rev-parse HEAD    # el hash, para aplicar algo inmutable
```

```sql
-- 2. En el Supabase de la casa, con el hash del commit
select public.alta_desde_repo(
  'https://raw.githubusercontent.com/Joacogol/calculadora-asistime/<hash>/worker/alta/esquemas/club-x-disenos.sql');

-- 3. El cliente, en la tabla de la casa
insert into public.clientes (marca, nombre, esquema, cobra) values
  ('club-x-disenos', 'Club X', 'club_x', true);
```

**4. Exponer el esquema.** En el panel del proyecto: Settings, API, «Exposed
schemas», agregar `club_x` a la lista. Es lo único que no se puede hacer por
SQL ni por API: PostgREST sólo sirve los esquemas que están en esa lista, y
hasta que esté contesta 406 diciendo cuáles expone.

**5. El registro**, para que el worker lo atienda:

```bash
python3 herramientas/registro.py agregar   # pide marca, URL, clave y esquema
```

La URL y la `service_role` son las de la casa, iguales para todos; lo que
cambia por cliente es el `esquema` y el `bucket`.

## `alta_desde_repo`

Corre el SQL que el repositorio ya tiene commiteado, en vez de que alguien
copie 38 KB a una consola. Sólo acepta URLs de este repositorio, y la ejecución
está limitada a `service_role`. Conviene pasarle siempre el hash de un commit y
no `main`: así lo que se aplicó queda registrado y es inmutable.
