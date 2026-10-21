Name:           photo-scan
Version:        0.1.0
Release:        1%{?dist}
Summary:        Qt6 GUI for SANE scanners with photo detection and cropping

License:        MIT
URL:            https://github.com/AHerling/photo-scan
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-setuptools
Requires:       python3 >= 3.12
Requires:       python3-pyside6
Requires:       python3-opencv
Requires:       sane-backends
Requires:       sane-airscan
Requires:       avahi

%description
Photo Scan is a simple Qt6 desktop app for SANE scanners on Linux. It helps you
scan documents and photographs with automatic photo detection and cropping.
Features: discover USB/network/AirScan/eSCL scanners, Simple and Pro modes,
preview and area selection, automatic photo detection and cropping, and
scanning to a user-selected folder.

%prep
%setup -q

%build
%py3_build

%install
%py3_install
install -Dm644 org.photo.scan.desktop %{buildroot}%{_datadir}/applications/org.photo.scan.desktop
install -Dm644 photo-scan.desktop %{buildroot}%{_datadir}/applications/photo-scan.desktop
install -Dm644 org.photo.scan.metainfo.xml %{buildroot}%{_datadir}/metainfo/org.photo.scan.metainfo.xml
install -Dm644 LICENSE %{buildroot}%{_licensedir}/%{name}/LICENSE
install -Dm644 photo-scan.png %{buildroot}%{_datadir}/icons/hicolor/48x48/apps/org.photo.scan.png 2>/dev/null || true
install -Dm644 photo-scan.png %{buildroot}%{_datadir}/icons/hicolor/256x256/apps/org.photo.scan.png 2>/dev/null || true

%files
%license LICENSE
%{python3_sitelib}/scan_gui/
%{python3_sitelib}/photo_scan-*.egg-info/
%{_bindir}/photo-scan
%{_bindir}/photo-scan-cli
%{_bindir}/scan-gui
%{_bindir}/scan-gui-cli
%{_datadir}/applications/org.photo.scan.desktop
%{_datadir}/applications/photo-scan.desktop
%{_datadir}/metainfo/org.photo.scan.metainfo.xml
%{_datadir}/icons/hicolor/*/apps/org.photo.scan.png
%{_licensedir}/%{name}/LICENSE

%changelog
* Tue Oct 21 2026 Photo Scan Contributors <noreply@github.com> - 0.1.0-1
- Initial package for Flathub/Bazaar compliance with Photo Scan branding.
- Added AirScan/eSCL support, preview/area selection, and Pro mode.
- Automatic photo detection and cropping.
