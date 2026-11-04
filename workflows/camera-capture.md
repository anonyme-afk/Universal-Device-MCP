# Workflow : Capture d'image avec une caméra

## Objectif

Détecter les caméras disponibles et capturer une image JPEG en mémoire.

## Preconditions

- `UDMCP_MEDIA_CAPTURE=true` doit être défini dans l'environnement du serveur (opt-in du propriétaire).
- Le paquet `[media]` est installé (`opencv-python-headless`, `sounddevice`, `numpy`).

## Séquence recommandée

1. **Vérifier que le média est autorisé** : `get_access_policy` ou vérifier `UDMCP_MEDIA_CAPTURE=true`.
2. **Découvrir les caméras** : `discover_cameras(max_index=8)`
   - Chaque sonde peut brièvement activer la caméra. Ne pas appeler automatiquement sans demande explicite.
3. **Capturer une image** : `capture_camera_image(camera_index=0)`
   - Retourne une image JPEG (≤ 900 Ko) encodée en base64, en mémoire uniquement.
   - L'image n'est pas écrite sur disque et n'est pas conservée dans l'historique.

## Outils MCP utilisés

- `discover_cameras`
- `capture_camera_image`

## Résultat attendu

- Liste des caméras détectées avec `device_id` et `index`.
- Image capturée : `mime_type: image/jpeg`, `image_base64`, taille en octets, `persisted: false`.

## Gestion des erreurs

| Situation | Action |
|-----------|--------|
| `PermissionError` | `UDMCP_MEDIA_CAPTURE` n'est pas défini. Demander au propriétaire de l'activer localement. |
| `ImportError` | Le paquet `[media]` n'est pas installé. Exécuter `pip install "universal-device-mcp[media]"`. |
| Aucune caméra trouvée | Aucune caméra accessible à l'index sondé. Vérifier que la caméra est branchée et pas utilisée par une autre application. |

## Considérations de sécurité

- Aucune caméra n'est activée automatiquement. `discover_cameras` et `capture_camera_image` requièrent un appel explicite.
- L'image est en mémoire uniquement, jamais écrite sur disque.
- Respecter les paramètres de confidentialité du système d'exploitation (Windows/macOS/Linux).
