#!/bin/sh

print_help()
{
cat << EOH
Prepares the source tree for configuration

Usage:
  autogen.sh [sydeps [--install-yum|--install-dnf]]

Options:

  sysdeps              prints out all dependencies
    --install-yum      install all dependencies ('sudo yum install \$DEPS')
    --install-dnf      install all dependencies ('sudo dnf install \$DEPS')

EOH
}

build_depslist()
{
    DEPS_LIST=`grep "^\(Build\)\?Requires:" *.spec.in | grep -v "%{name}" | tr -s " " | tr "," "\n" | cut -f2 -d " " | grep -v "^abrt" | sort -u | while read br; do if [ "%" = ${br:0:1} ]; then grep "%define $(echo $br | sed -e 's/%{\(.*\)}/\1/')" *.spec.in | tr -s " " | cut -f3 -d" "; else echo $br ;fi ; done | tr "\n" " "`
}

case "$1" in
    "--help"|"-h")
            print_help
            exit 0
        ;;
    "sysdeps")
            build_depslist

            if [ "$2" == "--install" ] || [ "$2" == "--install-dnf" ]; then
                set -x verbose
                sudo dnf install --setopt=strict=0 $DEPS_LIST
                set +x verbose
            elif [ "$2" == "--install-yum" ]; then
                set -x verbose
                sudo yum install $DEPS_LIST
                set +x verbose
            else
                echo $DEPS_LIST
            fi
            exit 0
        ;;
    *)
            ./gen-version
            autoreconf -i -f
        ;;
esac

