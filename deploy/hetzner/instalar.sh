#!/usr/bin/env bash
# Ejecutar en Hetzner desde un checkout revisado; no transfiere credenciales.
set -euo pipefail
repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
install_dir=/opt/asistime-disenador
revision="$(git -C "$repo_dir" rev-parse --short=12 HEAD)"
image_tag="asistime-disenador:git-${revision}"
if [[ $(id -u) != 0 ]]; then echo 'Ejecutar como root en el servidor.' >&2; exit 1; fi
if [[ -n $(git -C "$repo_dir" status --porcelain) ]]; then echo 'El checkout debe estar limpio.' >&2; exit 1; fi
docker build -f "$repo_dir/worker/Dockerfile.hetzner" -t "$image_tag" "$repo_dir/worker"
# Estas pruebas no tienen acceso a red ni credenciales.
for test in probar-marcas.py probar-crear-foto.py probar-encuadre-producto.py; do
  docker run --rm --network none --cpus=1.5 --memory=4g --entrypoint python "$image_tag" "herramientas/$test"
done
mkdir -p "$install_dir"/{config,modelos,piezas}
chmod 700 "$install_dir/config"
# No interrumpir un diseño en curso. Si hay uno, no se cambia el servicio.
state="$(systemctl show asistime-larrique.service -p ActiveState --value 2>/dev/null || true)"
if [[ "$state" == active || "$state" == activating || "$state" == deactivating ]]; then
  echo 'Hay un ciclo en curso; esperar y repetir la instalación.' >&2; exit 1
fi
systemctl stop asistime-larrique.timer 2>/dev/null || true
# Comprobar otra vez para cubrir el disparo del timer entre ambas lecturas.
state="$(systemctl show asistime-larrique.service -p ActiveState --value 2>/dev/null || true)"
if [[ "$state" == active || "$state" == activating || "$state" == deactivating ]]; then
  systemctl start asistime-larrique.timer
  echo 'Comenzó un ciclo; esperar y repetir.' >&2; exit 1
fi
cp -p "$install_dir/larrique.py" "$install_dir/larrique.anterior.py" 2>/dev/null || true
cp -p /etc/systemd/system/asistime-larrique.service "$install_dir/servicio.anterior" 2>/dev/null || true
install -m 644 "$repo_dir/deploy/hetzner/larrique.py" "$install_dir/larrique.py"
install -m 700 "$repo_dir/deploy/hetzner/configurar_claves.py" "$repo_dir/deploy/hetzner/configurar_fotos.py" "$install_dir/"
sed "s|asistime-disenador:encuadre-v3|$image_tag|" "$repo_dir/deploy/hetzner/asistime-larrique.service" > /etc/systemd/system/asistime-larrique.service
install -m 644 "$repo_dir/deploy/hetzner/asistime-larrique.timer" /etc/systemd/system/
systemctl daemon-reload
if [[ -f "$install_dir/config/credenciales.json" ]]; then
  systemctl enable --now asistime-larrique.timer
else
  echo 'Cargar credenciales con configurar_claves.py antes de activar asistime-larrique.timer.'
fi
