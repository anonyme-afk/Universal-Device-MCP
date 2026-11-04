# Workflow : Interaction avec un appareil

## Objectif

Envoyer une opération générique à une interface d'un appareil et vérifier que l'opération a réussi.

## Preconditions

- Un `device_id` et un `interface_id` connus (obtenus via `inspect_device`).
- La politique d'accès autorise l'opération (`get_access_policy` vérifié).
- L'appareil est connecté (`connect_device` si nécessaire).

## Séquence recommandée

1. **Vérifier la politique d'accès** : `get_access_policy`
   - Confirmer le mode (`safe`, `trusted`, `full`) et que l'opération n'est pas bloquée.
2. **Vérifier la connexion** : `inspect_device(device_id)`
   - Si `connected: false`, appeler `connect_device(device_id)`.
3. **Exécuter l'opération** : `communicate_device(device_id, interface_id, operation, data_hex?, session_id?, options?)`
   - `operation` : nom de l'opération (ex: `read`, `write`, `send`, `communicate`).
   - `data_hex` : données en hexadécimal si nécessaire.
   - `session_id` : réutiliser une session ouverte si l'interface le supporte.
4. **Vérifier le résultat** : confirmer l'absence d'erreur et la cohérence des données retournées.

## Outils MCP utilisés

- `get_access_policy`
- `inspect_device`
- `connect_device` (si nécessaire)
- `communicate_device`
- `open_interface` / `close_interface` (si session persistante requise)

## Résultat attendu

- Données retournées par l'appareil (pour une lecture).
- Confirmation d'envoi (pour une écriture).
- Aucun champ d'erreur dans la réponse.

## Gestion des erreurs

| Situation | Action |
|-----------|--------|
| `PermissionError` | La politique d'accès bloque l'opération. Demander à l'utilisateur de configurer une règle locale. |
| `RuntimeError: not currently connected` | Appeler `connect_device(device_id)` puis réessayer. |
| `TimeoutError` | L'appareil ne répond pas. Vérifier la connexion physique et relancer `inspect_device`. |
| `ValueError` | Paramètre invalide (ex: `data_hex` mal formé). Corriger les paramètres. |

## Considérations de sécurité

- Ne jamais exécuter une opération destructive (`flash`, `wipe`, `format`, `delete`, `remove`, `factory_reset`, `bootloader_unlock`, `execute`) : bloquée dans tous les modes.
- Respecter `max_write_bytes` (défaut 4096 octets).
- Pour les écritures répétées sur une même interface, envisager `open_interface` puis réutiliser la `session_id`.
