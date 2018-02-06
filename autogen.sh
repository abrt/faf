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
    PACKAGE=$1
    TEMPFILE=$(mktemp -u --suffix=.spec)
    sed 's/@PACKAGE_VERSION@/1/' < $PACKAGE.spec.in | sed 's/@.*@//' > $TEMPFILE
    rpmspec -P $TEMPFILE | grep "^\(Build\)\?Requires:" | \
        tr -s " " | tr "," "\n" | cut -f2- -d " " | \
        grep -v "^"$PACKAGE | sort -u | sed -E 's/^(.*) (.*)$/"\1 \2"/' | tr \" \'
    rm $TEMPFILE
}

case "$1" in
    "--help"|"-h")
            print_help
            exit 0
        ;;
    "sysdeps")
            DEPS_LIST=$( build_depslist faf)

            if [ "$2" == "--install" ] || [ "$2" == "--install-dnf" ]; then
                set -x verbose
                eval sudo dnf install --setopt=strict=0 $DEPS_LIST
                set +x verbose
            elif [ "$2" == "--install-yum" ]; then
                set -x verbose
                eval sudo yum install $DEPS_LIST
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

