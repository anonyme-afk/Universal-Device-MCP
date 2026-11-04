# Workflow : Surveillance des connexions d'appareils

## Objectif

Démarrer la surveillance en arrière-plan des connexions et déconnexions d'appareils, et réagir aux changements d'état.

## Preconditions

- Le serveur MCP est démarré.
- `UDMCP_AUTO_MONITOR` peut être laissé à sa valeur par défaut (`false` : démarrage explicite requis).

## Séquence recommandée

1. **Démarrer le moniteur** : `start_device_monitor(interval_seconds=5.0)`
   - Le moniteur vérifie périodiquement les appareils connectés et déconnectés.
2. **Lire les événements** : `get_device_events(after_id=0, limit=100)`
   - Récupérer les événements de connexion/déconnexion depuis le dernier ID connu.
3. **Agir sur un événement** :
   - `connected` : inspecter le nouvel appareil (`inspect_device`).
   - `disconnected` : marquer l'appareil comme indisponible, ne plus tenter d'opérations sur son `device_id`.
4. **Arrêter le moniteur** : `stop_device_monitor()` quand la surveillance n'est plus nécessaire.

## Outils MCP utilisés

- `start_device_monitor`
- `stop_device_monitor`
- `get_device_events`
- `inspect_device`

## Résultat attendu

- Événements avec `type` (`connected` ou `disconnected`), `device_id`, `details` et `created_at`.
- État de connexion à jour pour chaque appareil connu.

## Gestion des erreurs

| Situation | Action |
|-----------|--------|
| Événement sur un appareil inconnu | Relancer `discover_devices` pour mettre à jour l'inventaire. |
| Appareil se déconnecte pendant une opération | L'opération échoue avec `RuntimeError` ou `TimeoutError`. Relancer `inspect_device` pour confirmer l'état. |

## Considérations de sécurité

- Le moniteur est en lecture seule sur l'état des appareils. Il ne modifie aucun matériel.
- Le moniteur est arrêté par défaut et doit être démarré explicitement.
