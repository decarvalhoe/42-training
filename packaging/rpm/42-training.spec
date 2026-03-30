Name:           42-training
Version:        0.1.0
Release:        1%{?dist}
Summary:        42 Lausanne learning platform with agentic mentor architecture

License:        MIT
URL:            https://github.com/decarvalhoe/42-training
Source0:        %{name}-%{version}.tar.gz

BuildArch:      x86_64
BuildRequires:  python3-devel, nodejs >= 20, npm

Requires:       python3 >= 3.11
Requires:       python3-pip
Requires:       nodejs >= 20
Requires:       npm
Requires:       postgresql-server >= 16
Requires:       redis >= 7
Requires:       tmux
Requires:       systemd

%description
Triple-track learning system (Shell, C, Python+AI) for 42 Lausanne.
Includes API server, AI gateway with mentor orchestration, and
Next.js web frontend with terminal integration.

%prep
%setup -q

%install
mkdir -p %{buildroot}/opt/42-training
mkdir -p %{buildroot}/etc/42-training
mkdir -p %{buildroot}/%{_unitdir}
mkdir -p %{buildroot}/%{_bindir}

# Application files
cp -r services %{buildroot}/opt/42-training/
cp -r apps %{buildroot}/opt/42-training/
cp -r packages %{buildroot}/opt/42-training/
cp -r scripts %{buildroot}/opt/42-training/
cp progression.json %{buildroot}/opt/42-training/

# Systemd units (from packaging dir)
install -m 644 packaging/rpm/42-training-api.service %{buildroot}/%{_unitdir}/
install -m 644 packaging/rpm/42-training-gateway.service %{buildroot}/%{_unitdir}/
install -m 644 packaging/rpm/42-training-web.service %{buildroot}/%{_unitdir}/

# CLI wrapper
install -m 755 packaging/deb/build-deb.sh /dev/null  # placeholder
cat > %{buildroot}/%{_bindir}/42-training <<'CLI'
#!/usr/bin/env bash
set -euo pipefail
case "${1:-}" in
    start)  sudo systemctl start 42-training-api 42-training-gateway 42-training-web ;;
    stop)   sudo systemctl stop 42-training-web 42-training-gateway 42-training-api ;;
    status) for s in api gateway web; do systemctl is-active "42-training-$s"; done ;;
    *)      echo "Usage: 42-training {start|stop|status}" ;;
esac
CLI

%post
# Create system user
if ! id -u training &>/dev/null; then
    useradd --system --home-dir /opt/42-training --shell /sbin/nologin training
fi

# Python virtualenvs
for svc in api ai_gateway; do
    python3 -m venv "/opt/42-training/services/$svc/.venv"
    "/opt/42-training/services/$svc/.venv/bin/pip" install -q \
        -r "/opt/42-training/services/$svc/requirements.txt"
done

# Node dependencies
cd /opt/42-training/apps/web && npm ci --production -q 2>/dev/null || npm install --production -q

# Default config
if [ ! -f /etc/42-training/env ]; then
    cat > /etc/42-training/env <<ENVFILE
DATABASE_URL=postgresql+asyncpg://training:training@localhost:5432/training
REDIS_URL=redis://localhost:6379/0
API_PORT=8000
AI_GATEWAY_PORT=8100
AI_GATEWAY_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_AI_GATEWAY_URL=http://localhost:8100
PORT=3000
APP_SECRET_KEY=$(openssl rand -hex 32)
ENVFILE
    chmod 600 /etc/42-training/env
    chown training:training /etc/42-training/env
fi

chown -R training:training /opt/42-training
%systemd_post 42-training-api.service 42-training-gateway.service 42-training-web.service

%preun
%systemd_preun 42-training-api.service 42-training-gateway.service 42-training-web.service

%postun
%systemd_postun_with_restart 42-training-api.service 42-training-gateway.service 42-training-web.service

%files
%defattr(-,root,root,-)
/opt/42-training/
%config(noreplace) /etc/42-training/
%{_unitdir}/42-training-api.service
%{_unitdir}/42-training-gateway.service
%{_unitdir}/42-training-web.service
%{_bindir}/42-training

%changelog
* Sat Mar 29 2026 42-training <contact@42lausanne.ch> - 0.1.0-1
- Initial RPM package
