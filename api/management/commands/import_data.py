import os
import json
import csv
import xml.etree.ElementTree as ET
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from datetime import datetime
from api.models import (
    Estado, Municipio
)
from django.utils.dateparse import parse_datetime



class Command(BaseCommand):
    help = 'Importa dados de estados e municípios'

    def handle(self, *args, **kwargs):
        self.carregarEstados()
        self.carregarMunicipios()
        pass

    def carregarEstados(self):
        with open('/app/assets/estados.json') as f:
            estados_data = json.load(f)
            for estado_data in estados_data:
                Estado.objects.get_or_create(
                    id = estado_data['ID'],
                    id_ibge = estado_data['id_ibge'],
                    nome=estado_data['Nome'],
                    uf=estado_data['Sigla'],
                    regiao=estado_data['Regiao'],
                    pais='Brasil',
                    latitude=estado_data['Latitude'],
                    longitude=estado_data['Longitude']
                )

        self.stdout.write(self.style.SUCCESS('Estados importados com sucesso.'))

    def carregarMunicipios(self):
        with open('/app/assets/cidades.json') as f:
            municipios_data = json.load(f)
            for municipio_data in municipios_data:
                estado = Estado.objects.filter(id=municipio_data['estado']).first()
                Municipio.objects.get_or_create(
                    id = municipio_data['ID'],
                    codigo_ibge = municipio_data['id_ibge'],
                    nome=municipio_data['nome'],
                    estado_id=municipio_data['estado'],
                    capital=municipio_data['capital']
                )

        self.stdout.write(self.style.SUCCESS('Municípios importados com sucesso.'))
