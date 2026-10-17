# Harbor Market Tycoon: zehn Planetenmodelle

Zehn stilisierte Low-Poly-Planeten für „Harbor Market Tycoon“ auf Colossal Squid Games. Jeder Planet hat eine große, wirklich ebene und unbebaute Baufläche für spätere Shops.

| # | Planet | Charakter |
|---|--------|-----------|
| 01 | Pelagia | Der freundliche Ozeanplanet |
| 02 | Coralune | Die lebendige Korallenwelt |
| 03 | Verdantide | Der grüne Inselgarten |
| 04 | Dunewake | Die maritime Wüstenwelt |
| 05 | Frostharbor | Der gefrorene Hafen |
| 06 | Ember Shoal | Die Vulkaninsel |
| 07 | Prismara | Der Kristallozean |
| 08 | Sporehaven | Die leuchtende Pilzwelt |
| 09 | Ringhaven | Der kosmische Handelshafen |
| 10 | Abyssal Crown | Die geheimnisvolle Tiefseewelt |

## Dateien

- `HarborMarket_Planets.blend`: Blender-Datei (erstellt mit Blender 5.2) mit einer Collection pro Planet. Die zehn Planeten liegen nebeneinander im Übersichtsraster.
- `glb/NN_Name.glb`: ein GLB pro Planet, zentriert im Ursprung.
- `previews/NN_Name.png`: Vorschau pro Planet mit transparentem Hintergrund, 1200 × 1200 px.
- `previews/NN_Name.jpg`: dieselbe Vorschau auf ruhigem Hintergrund.
- `previews/00_Overview.png` und `.jpg`: gemeinsame Übersicht aller zehn Modelle.
- `planets.json`: Paletten, Deko-Zählungen, Dreiecke und Bauflächen-Maße pro Planet.
- `generator/`: Python-Skripte, die alles reproduzierbar erzeugen.

## Aufbau der Blender-Datei

```
00_Preview_Rig      Key_Sun, Rim_Sun, Fill_Sun, Preview_Cam, <Planet>_Cam × 10
01_Pelagia
├─ Pelagia_Planet     Pelagia_Body, Pelagia_Ocean, Pelagia_Terraces
├─ Pelagia_BuildArea  Pelagia_BuildArea
└─ Pelagia_Deco       Pelagia_Deco_Palms, …_Piers, …_Lighthouse, …
02_Coralune … 10_AbyssalCrown   (gleiches Schema)
```

- **Root:** Alle Objekte eines Planeten hängen an `<Planet>_Root`, einem Empty. Wer das Empty verschiebt, verschiebt den ganzen Planeten mitsamt seiner Vorschaukamera.
- **Getrennt editierbar:** Planetenkörper, Baufläche und Deko liegen in eigenen Collections. Die Deko ist pro Kategorie ein Objekt, zum Beispiel Palmen, Stege oder Kristalle.
- **Materialien:** Jeder Planet nutzt eine eigene, begrenzte Palette mit dem Präfix `<Planet>_`. Leuchtakzente sind emissive Materialien.

## Maßstab und Baufläche

- **Maßstab:** 1 Blender-Einheit entspricht 1 m. Der Meeresspiegel liegt bei Radius 1,0.
- **Baufläche:** Sie ist exakt planar bei z = 1,035 bis 1,04, bei einem Radius von etwa 0,46 bis 0,50. Das ergibt rund 0,72 bis 0,74 m² Fläche. Auf der Baufläche liegt keine Deko.
- **Daten im Objekt:** Das Objekt `<Planet>_BuildArea` trägt diese Werte als Custom Properties: `build_surface_z`, `build_radius_min`, `build_radius_max` und `build_area_m2`. Im GLB stehen sie als `extras` am Knoten.
- **Ausrichtung im GLB:** Die Blender-Achse +Z wird im GLB zu +Y. Die Vorderseite (Blender −Y, Kameraseite) zeigt im GLB nach +Z.

## Kamera und Licht der Vorschauen

- **Kamera:** orthografisch, 50° über dem Horizont, Blick von vorne (−Y), Ortho-Scale 3,05. Die Kamera ist für alle Planeten gleich.
- **Licht:** eine warme Key-Sonne von oben links, eine kühle Rim-Sonne von hinten rechts und ein schwaches Fill-Licht.
- **Rendering:** Cycles mit 96 Samples und Denoising, Farbtransformation AgX Punchy.

## Neu erzeugen

```bash
pip install bpy==5.2.2 pillow numpy      # Python 3.13
python generator/run.py --out out --res 1200 --samples 96 --glb --save --overview
python generator/compose.py out/previews out/previews
```

Mit `--only 3,7` werden nur einzelne Planeten gebaut.
