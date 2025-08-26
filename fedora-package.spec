Name:           safeeyes
Version:        3.0.0
Release:        1%{?dist}
Summary:        Prevent eye strain with Safe Eyes – an essential screen break reminder

License:        GPL-3.0-or-later
URL:            https://github.com/slgobinath/SafeEyes
Source0:        %{name}-%{version}.tar.gz
BuildArch:      noarch

BuildRequires:  python3-devel, python3-packaging, python3-setuptools, gettext
BuildRequires:  python3-pip
Requires:       python3
Requires:       python3-gobject
Requires:       python3-xlib
Requires:       python3-babel
Requires:       python3-croniter
Requires:       python3-packaging
Requires:       gobject-introspection
Requires:       gir1.2-notify-0.7
Requires:       gir1.2-gtk-4.0
Requires:       ffmpeg
Requires:       python3-pywayland

%description
Safe Eyes is a simple tool to remind you to take periodic breaks for your eyes. This
is essential for anyone spending more time on the computer to avoid eye strain and other
physical problems.

%prep
# Expect the sdist to be named %{name}-%{version}.tar.gz which expands to safeeyes-3.0.0.tar.gz
# and to unpack to a top-level directory named %{name}-%{version}.
%autosetup -n %{name}-%{version}

%build
# Use a simple sdist build; compile translations
%py3_build

%install
%py3_install

%files
%license LICENSE
%doc README.md
%{python3_sitelib}/safeeyes

%changelog
* Tue Aug 26 2025 SafeEyes Maintainer - 3.0.0-1
- Initial Fedora package
