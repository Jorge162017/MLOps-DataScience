"""Paquete local de registros y salidas; nunca envía archivos a servicios externos."""
import argparse
from pathlib import Path
import sqlite3
import tempfile
import zipfile
from seguimiento import settings
from utilidades import ROOT


def export(destination,output,demo):
    uri,artifacts=settings();database=Path(uri.removeprefix('sqlite:///'))
    destination=Path(destination);destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        db=Path(td)/'mlflow.db'
        with sqlite3.connect(database) as source,sqlite3.connect(db) as target:source.backup(target)
        with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as archive:
            archive.write(db,'mlflow_data/mlflow.db')
            for root,prefix in [(artifacts,'mlflow_data/artifacts'),(Path(output),'resultados_peten'),(Path(demo),'demo_sintetico')]:
                if root.exists():
                    for path in root.rglob('*'):
                        if path.is_file() and path.suffix not in ['.xlsx','.zip']:
                            archive.write(path,str(Path(prefix)/path.relative_to(root)))
    return destination


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'resultados_peten')
    parser.add_argument('--demo',type=Path,default=ROOT/'demo_sintetico')
    parser.add_argument('--zip',type=Path,default=ROOT/'.entrega/lab11_registros_y_resultados.zip')
    args=parser.parse_args();print(export(args.zip,args.output,args.demo))
