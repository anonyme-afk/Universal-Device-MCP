# Workflow : Inspection des interfaces d'un appareil

## Objectif

Comprendre quelles interfaces un appareil spécifique expose et quelles opérations peuvent y être effectuées.

## Preconditions

- Un `device_id` connu (obtenu via `discover_devices` ou `list_known_devices`).

## Séquence recommandée

1. **Inspecter l'appareil** : `inspect_device(device_id)`
   - Vérifier que l'appareil est connecté (`connected: true`).
   - Noter la liste des `interfaces` (chaque interface a un `id` et un `kind`).
2. **Expliquer une interface spécifique** : `explain_device_interface(device_id, interface_id)`
   - Obtenir une description lisible de l'interface et des opérations supportées.
3. **Voir les capacités globales** : `get_device_capabilities(device_id)`
   - Résumé rapide des capacités de l'appareil.

## Outils MCP utilisés

- `inspect_device`
- `explain_device_interface`
- `get_device_capabilities`

## Résultat attendu

Pour chaque interface :
- `id` : identifiant de l'interface (utilisé dans `communicate_device`, `open_interface`, etc.).
- `kind` : type d'interface (ex: `adb-shell`, `usb-bulk`, `gatt-characteristic`, `serial-port`).
- Description des opérations lisibles par l'agent.

## Gestion des erreurs

| Situation | Action |
|-----------|--------|
| `KeyError: Unknown device` | Le `device_id` n'existe pas. Relancer `discover_devices` pour obtenir un ID valide. |
| Appareil non connecté | Appeler `connect_device(device_id)` puis réinspecter. |
| Aucune interface retournée | L'appareil n'expose aucune interface accessible dans l'état actuel. |

## Considérations de sécurité

- Cette opération est en lecture seule. Elle ne modifie aucun matériel.
- Ne jamais supposer qu'une interface supporte une opération sans l'avoir confirmée via `explain_device_interface`.
