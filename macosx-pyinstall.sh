#!/usr/bin/env bash

usage() {
    echo "macosx-pyinstall.sh --version <Version Number>"
    echo "--version    The version number to give Edproxy. Ex. 2.0.0"
    exit 0
}

VERSION=

if [ $# -eq 0 ]; then
    usage
fi

while [ $# -gt 0 ]; do
      case "$1" in
          -v|--version)
              shift
              VERSION=$1
                ;;
           *)
                usage
                ;;
      esac
      shift
done

pyinstaller --clean --noconfirm --windowed --icon=edicon.icns edproxy.py

CUR_DIR=`pwd`
DIST_DIR=$CUR_DIR/dist/edproxy.app/Contents/MacOS
RM_FILES="libwx_baseu-3.0.dylib libwx_baseu_xml-3.0.dylib libwx_osx_cocoau_adv-3.0.dylib libwx_osx_cocoau_core-3.0.dylib libwx_osx_cocoau_html-3.0.dylib"
OUT_NAME="edproxy-macosx-$VERSION.dmg"

cd $DIST_DIR

for rmf in $RM_FILES
do
    rm -f $rmf
done

ln -sf libwx_baseu-3.0.0.2.0.dylib libwx_baseu-3.0.dylib
ln -sf libwx_baseu_xml-3.0.0.2.0.dylib libwx_baseu_xml-3.0.dylib
ln -sf libwx_osx_cocoau_adv-3.0.0.2.0.dylib libwx_osx_cocoau_adv-3.0.dylib
ln -sf libwx_osx_cocoau_core-3.0.0.2.0.dylib libwx_osx_cocoau_core-3.0.dylib
ln -sf libwx_osx_cocoau_html-3.0.0.2.0.dylib libwx_osx_cocoau_html-3.0.dylib

cd $CUR_DIR

if [ -e "$OUT_NAME" ]; then
    rm -f $OUT_NAME
fi

dmgbuild -s macosx-dmg-settings.py -D app=./dist/edproxy.app "Edproxy" $OUT_NAME
