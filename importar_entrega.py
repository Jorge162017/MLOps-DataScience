"""Restaura un paquete en una carpeta nueva y reubica las URI locales de MLflow."""
import argparse
from pathlib import Path
import sqlite3
import zipfile


def restore(archive,destination):
    destination=Path(destination).resolve()
    if destination.exists() and any(destination.iterdir()):raise ValueError('La carpeta de destino debe estar vacía')
    destination.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        for item in z.infolist():
            if not (destination/item.filename).resolve().is_relative_to(destination):raise ValueError('Ruta no válida en paquete')
        z.extractall(destination)
    root=destination/'mlflow_data/artifacts'
    with sqlite3.connect(destination/'mlflow_data/mlflow.db') as db:
        for table,column,id_col in [('experiments','artifact_location','experiment_id'),('runs','artifact_uri','run_uuid')]:
            for key,value in db.execute(f'SELECT {id_col},{column} FROM {table}').fetchall():
                if value and '/artifacts/' in value:
                    suffix=value.split('/artifacts/',1)[1]
                    db.execute(f'UPDATE {table} SET {column}=? WHERE {id_col}=?',((root/suffix).as_uri(),key))
    return destination


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('archive',type=Path);p.add_argument('destination',type=Path)
    a=p.parse_args();print(restore(a.archive,a.destination))
