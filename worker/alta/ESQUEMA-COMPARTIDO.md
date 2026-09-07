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
insert into public.clientes (marca, nombre, esquema, bucket, cobra) values
  ('club-x-disenos', 'Club X', 'club_x', 'disenos-club-x', true);

-- 4. Exponer el esquema, para que PostgREST lo sirva
select public.exponer_esquema('club_x');
```

**5. La clave de la API**, para que el cliente pueda pedir desde el chat:

```sql
select public.alta_clave('club-x-disenos', null, 'tools de Asistime');
```

Devuelve la clave UNA vez —después queda sólo su SHA-256— y va escrita en el
código de las tools del agente, igual que hasta ahora. Ver «Una clave por
cliente» más abajo.

**6. Las plantillas**, para que la base arranque con lo que trae el despliegue:

```sql
with base as (select
  'https://raw.githubusercontent.com/Joacogol/calculadora-asistime/<hash>/worker/.claude/skills/club-x-disenos/plantillas/' as u)
select public.sembrar_plantilla_desde_repo('club_x', p, (select u from base) || p)
  from unnest(array['foto','titular']) as p;   -- los slugs del cliente
```

Es lo mismo que hace `herramientas/sembrar-plantillas.py`, pero sin necesitar la
`service_role` ni un `.env`: lee el HTML y el contrato del repositorio y llama a
la misma `guardar_plantilla` del esquema del cliente, así la versión, el
historial y la publicación quedan igual que si los hubiera subido el worker.
Sólo lee de este repositorio.

**7. El registro**, para que el worker lo atienda:

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


## Una clave por cliente

Las funciones de borde —`api-disenos`, `api-plantillas`, `api-fotos`,
`api-reels`, `api-publicar` y `api-subir`— vivían en el proyecto de UN cliente.
Ahí, verificar que la clave era la buena alcanzaba para saber en qué base
escribir: no había otra.

Compartiendo proyecto eso ya no cierra. La misma función atiende a todos, así
que la clave además tiene que decir **de quién es**: de eso salen el esquema
donde están sus tablas y el bucket donde van sus archivos. Por eso
`identificar()` devuelve un cliente y no un sí o un no, y por eso hay una tabla:

| | |
|---|---|
| `public.claves_api` | el SHA-256 de cada clave, con su marca y su usuario |
| `public.claves_resueltas` | la vista que junta eso con el esquema y el bucket de `public.clientes` |
| `public.alta_clave(marca)` | acuña una clave nueva y devuelve la original una sola vez |

**Se guarda el hash, nunca la clave.** La clave viaja escrita en el código de
una tool de Asistime —eso no cambió y está explicado en `DESPLEGAR.md`—, pero
del lado de la base no queda nada que sirva para entrar: quien lea la tabla se
lleva hashes. La comparación la hace Postgres sobre un hash completo, así que
tampoco hay tiempos que medir para adivinar la original.

**El cliente de la casa sigue entrando por `API_CLAVE`.** Asistime vive en
`public` y se autentica contra el secreto del proyecto, sin tocar la base. Es a
propósito: una migración a medias —o una tabla vacía— nunca lo deja afuera. Sus
valores salen de las variables `ESQUEMA` (vacía), `BUCKET` (`disenos`) y
`USUARIO_ID`, que ya estaban.

### Lo que se arregló de paso

`api-reels` sella la elección de proveedor para que el agente no pueda elegir
sin haber preguntado. El sello se hacía con la propia `API_CLAVE` — que está
escrita en claro en el código de la tool, así que cualquiera que la leyera podía
fabricar uno. Ahora se hace con la `service_role`, que no sale del servidor,
con la marca adentro para que un sello de un cliente no valga en la base de
otro.


## Exponer el esquema, sin el panel

PostgREST sólo sirve los esquemas que están en su lista, y hasta que el del
cliente esté ahí **todo lo suyo contesta 406**: un alta que quedó a medias sin
que nada se vea roto. Era el único paso que había que hacer a mano en el panel
—Settings, API, «Exposed schemas»— y por eso era el que se iba a olvidar.

`public.exponer_esquema('club_x')` lo hace en SQL: PostgREST lee esa lista de
la variable `pgrst.db_schemas` del rol `authenticator`, así que se puede
escribir desde la base. Después avisa dos veces, y las dos hacen falta:
`reload config` para que relea la lista y `reload schema` para que relea las
tablas. Sin el segundo contesta 404 «no encuentro la tabla», que es la misma
espera disfrazada de otro error.

`public.esconder_esquema('club_x')` es la contraria, para dar de baja.

Si alguien toca «Exposed schemas» en el panel, gana el panel: lo que se guarda
ahí se escribe sobre esta lista. Vale la pena mirarla —`select rolconfig from
pg_roles where rolname = 'authenticator'`— si un cliente que andaba empieza a
contestar 406 de un día para el otro.
