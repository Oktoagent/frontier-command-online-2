# Harbor Market Tycoon – Modell-Export (GLB)

Low-Poly-Modelle zum Modell-Designpaket „Kunden, NPCs und Raumschiffe für zehn Planeten“. Die Designblätter mit drehbaren Vorschauen liegen im Claude-Design-Canvas. Dieser Ordner enthält die daraus exportierten Modelldateien.

## Inhalt

| Ordner | Dateien | Inhalt |
|---|---|---|
| `figuren/<Planet>/` | 50 | je Planet 3 Kunden (`-k1` bis `-k3`) und 2 lokale NPCs (`-n1`, `-n2`), neutrale Pose |
| `personal/<Rolle>/` | 55 | 5 Grundmodelle (`*_grundmodell.glb`) und je Rolle 10 Planeten-Outfits |
| `schiffe/<Planet>/` | 40 | 20 Schiffe (`-p` Passagier, `-f` Fracht), je `_gelandet` (Tür bzw. Rampe zu) und `_offen` |

`index.json` listet jede Datei mit Bauteilanzahl, Dreiecken, Höhe in F und Dateigröße.

## Maßstab und Ausrichtung

- **1 F (Standardfigur) = 0,025 Blender-Einheiten.** Grundlage ist das README der Planeten-ZIP: 1 Einheit = 1 m, Meeresspiegel bei Radius 1,0, Baufläche eben bei z = 1,035 bis 1,04 mit Radius ≈ 0,47 bis 0,50.
- Standardfigur ≈ 0,025 hoch, Schiffstür 0,019 × 0,032, Thekenblock (nur in den Blättern) 0,030 × 0,012 × 0,014.
- Wie bei den Planeten-GLBs zeigt +Y nach oben (Blender +Z) und die Vorderseite nach +Z (Blender −Y). Der Ursprung liegt am Boden unter der Figur bzw. dem Schiff.

## Aufbau

- Ein Knoten pro Bauteil, zum Beispiel `kopf`, `haare`, `arm_l`, `hand_l`, `bein_r`, `schuh_r`, `schürze`, `gegenstand_basket`, `triebwerk_l`, `landebein_3`, `tür`, `treppe`, `rampe`, `frachtmodul_2`. So bleiben Hände, Taschen, Landebeine, Rampen und Triebwerke getrennt bearbeitbar.
- Materialien heißen `HM_<hex>` und sind matt. Leuchtende Teile tragen den Zusatz `_leuchtend` und haben einen Emissionswert. Es gibt keine Texturen und keine UVs.
- Normalen sind nicht gespeichert. glTF-Importer berechnen dann flache Normalen, was dem facettierten Low-Poly-Look entspricht.

## Grenzen

- Figuren liegen nur in der neutralen Pose vor. Gehend, tragend und arbeitend gibt es nur in den Browser-Vorschauen, denn die Dateien enthalten keine Skelette und keine Animationen.
- Eine neue `.blend`-Datei gibt es nicht. Import in Blender: Datei › Import › glTF 2.0, danach auf der Baufläche des jeweiligen Planeten platzieren.
