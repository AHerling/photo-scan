%global forgeurl https://github.com/AHerling/photo-scan

Name:           photo-scan
Version:        0.2.0
Release:        1%{?dist}
Summary:        Desktop app for SANE scanners with photo detection and cropping

License:        MIT
URL:            %{forgeurl}
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel >= 3.12
BuildRequires:  python3-setuptools
BuildRequires:  python3-wheel
BuildRequires:  python3-pyside6
BuildRequires:  python3-opencv
BuildRequires:  python3-numpy
BuildRequires:  desktop-file-utils

Requires:       python3 >= 3.12
Requires:       python3-pyside6
Requires:       python3-opencv
Requires:       python3-numpy
Requires:       sane-backends
Requires:       sane-airscan
Requires:       avahi

%description
Photo Scan is a desktop application for SANE scanners on Linux. It helps you
scan documents and photographs, and automatically detects and crops the photos
on the scanner bed.

* Simple mode for everyday scanning: pick a scanner, colour mode, resolution
  and destination folder, then press one button.
* Pro mode for full control: every SANE option the device exposes, a live bed
  preview and interactive area selection.
* Automatic photo detection, including cropping several photos out of a single
  scan.
* Automatic file numbering in the folder you choose.

USB scanners need the scanner and lp groups; network scanners need the Avahi
daemon running.

%prep
%autosetup -n %{name}-%{version}

%build
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files -l scan_gui

desktop-file-install --dir %{buildroot}%{_datadir}/applications \
    data/io.github.AHerling.photo-scan.desktop
desktop-file-validate \
    %{buildroot}%{_datadir}/applications/io.github.AHerling.photo-scan.desktop

install -Dm644 data/io.github.AHerling.photo-scan.metainfo.xml \
    %{buildroot}%{_datadir}/metainfo/io.github.AHerling.photo-scan.metainfo.xml

install -Dm644 data/icons/hicolor/scalable/apps/io.github.AHerling.photo-scan.svg \
    %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/io.github.AHerling.photo-scan.svg
for size in 16 24 32 48 64 128 256; do
    install -Dm644 data/icons/hicolor/${size}x${size}/apps/io.github.AHerling.photo-scan.png \
        %{buildroot}%{_datadir}/icons/hicolor/${size}x${size}/apps/io.github.AHerling.photo-scan.png
done

%check
%{__python3} -m unittest discover -s tests

%files -f %{pyproject_files}
%license LICENSE
%{_bindir}/photo-scan
%{_datadir}/applications/io.github.AHerling.photo-scan.desktop
%{_datadir}/metainfo/io.github.AHerling.photo-scan.metainfo.xml
%{_datadir}/icons/hicolor/*/apps/io.github.AHerling.photo-scan.*

%changelog
* Wed Oct 21 2026 Photo Scan Contributors <noreply@github.com> - 0.2.0-1
- Initial Fedora package.
