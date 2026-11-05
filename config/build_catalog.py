"""Rebuild the transparent, provisional ecological catalogue (no trained parameters)."""
from pathlib import Path
import yaml

# id, Catalan name, host habitat, months, elevation bounds, rain window/optimum,
# minimum/optimal/maximum mean temperature, frost tolerance.
PROFILES = [
 ('lactarius_deliciosus','Pinetell','Pinedes', [9,10,11,12],0,1800,18,75,2,13,24,4),
 ('lactarius_sanguifluus','Rovelló','Pinedes calcàries',[9,10,11,12],0,1500,18,65,3,13,23,4),
 ('boletus_edulis','Cep','Fagedes, avetoses i pinedes',[6,7,8,9,10,11],500,2300,21,90,3,13,23,3),
 ('boletus_aereus','Sureny','Alzinars, suredes i rouredes',[6,7,8,9,10],0,1200,18,70,8,19,28,2),
 ('boletus_aestivalis','Cep d’estiu','Rouredes i castanyedes',[5,6,7,8,9],200,1600,18,80,7,18,27,2),
 ('boletus_pinophilus','Cep de pi','Pinedes montanes',[5,6,9,10,11],600,2200,21,90,2,12,22,4),
 ('craterellus_lutescens','Camagroc','Pinedes humides amb molsa',[9,10,11,12,1],100,1800,25,95,0,10,20,6),
 ('craterellus_cornucopioides','Trompeta de la mort','Fagedes, rouredes i alzinars humits',[8,9,10,11,12],200,1700,25,100,3,12,23,4),
 ('craterellus_tubaeformis','Rossinyolic','Boscos humits de coníferes i caducifolis',[9,10,11,12],400,2000,25,95,0,9,19,6),
 ('cantharellus_cibarius','Rossinyol','Fagedes, castanyedes, suredes i rouredes',[5,6,7,8,9,10,11],100,1800,25,100,5,15,25,3),
 ('hygrophorus_latitabundus','Llenega negra','Pinedes calcàries',[10,11,12,1],100,1500,20,80,1,9,18,5),
 ('hygrophorus_marzuolus','Marçot','Avetoses, pinedes i fagedes montanes',[2,3,4,5],700,2200,21,80,-1,6,15,7),
 ('tricholoma_terreum','Fredolic','Pinedes',[10,11,12,1],0,2000,20,70,-2,7,17,8),
 ('tricholoma_portentosum','Verderol','Pinedes silícies',[10,11,12],400,2000,21,80,0,8,18,6),
 ('hydnum_repandum','Llengua de bou','Boscos caducifolis, alzinars i pinedes',[8,9,10,11,12],100,1800,25,90,1,11,22,6),
 ('amanita_caesarea','Ou de reig','Alzinars, suredes i castanyedes',[7,8,9,10],0,1200,18,70,10,20,29,1),
 ('macrolepiota_procera','Apagallums','Clarianes, marges i prats',[5,6,9,10,11],0,1800,18,65,5,15,25,3),
 ('marasmius_oreades','Cama-sec','Prats i pastures',[4,5,6,9,10,11],0,2200,14,50,4,14,25,4),
 ('calocybe_gambosa','Moixernó','Prats i vores de bosc',[3,4,5,6],400,2200,21,75,2,11,21,4),
 ('agaricus_campestris','Xampinyó silvestre','Prats i pastures',[4,5,6,9,10,11],0,2000,14,55,5,15,25,3),
 ('morchella_elata','Múrgola negra','Pinedes montanes i sòls remoguts',[3,4,5,6],500,2200,21,80,2,10,20,4),
 ('morchella_esculenta','Múrgola','Boscos de ribera i sòls frescos',[3,4,5],0,1600,21,80,4,12,22,3),
 ('pleurotus_eryngii','Gírgola de panical','Pastures amb panical',[4,5,10,11],0,1600,18,60,3,12,23,4),
 ('cyclocybe_aegerita','Pollancró','Fusta de pollancre i altres arbres de ribera',[4,5,6,7,8,9,10,11],0,1000,18,70,6,17,27,2),
]

if __name__ == '__main__':
    catalog = {}
    for key,name,habitat,months,lo,hi,window,rain,tlo,topt,thi,frost in PROFILES:
        catalog[key] = {'common_name': name, 'scientific_name': key.replace('_',' ').capitalize(),
            'habitat': habitat, 'months': months, 'altitude_min': lo, 'altitude_max': hi,
            'profile_status': 'provisional; expert review and field calibration required',
            'meteo_triggers': {'rain_window_days': window, 'rain_optimal_mm': rain,
                'temp_min_celsius': tlo, 'temp_optimal_celsius': topt,
                'temp_max_celsius': thi, 'frost_penalty_days': frost}}
    Path(__file__).with_name('species_rules.yaml').write_text(
        yaml.safe_dump(catalog, allow_unicode=True, sort_keys=False), encoding='utf-8')
