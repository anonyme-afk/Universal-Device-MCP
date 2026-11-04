# Workflow : Découverte du matériel connecté

## Objectif

Lister tous les périphériques matériels accessibles par les adaptateurs locaux (USB, série, Bluetooth, réseau mDNS, Android ADB, iOS) et en obtenir un inventaire structuré.

## Preconditions

- Le serveur MCP Universal Device MCP est démarré.
- L'agent a accès aux outils `discover_devices`, `discover_wireless_devices`, `list_known_devices`, `get_runtime_status`.

## Séquence recommandée

1. **Vérifier l'état du serveur** : `get_runtime_status`
   - Confirmer que les adaptateurs souhaités sont disponibles (pas d'erreur de dépendance manquante).
2. **Découvrir les appareils locaux** : `discover_devices`
   - Optionnel : filtrer par transport si vous cherchez un type spécifique (`transports=["usb"]`, `transports=["serial"]`, etc.).
3. **Découvrir les appareils sans fil** : `discover_wireless_devices`
   - Pour les services BLE, mDNS, Android ADB et iOS annoncés localement.
4. **Lister les appareils déjà connus** : `list_known_devices`
   - Pour éviter de redécouvrir des appareils déjà en base.

## Outils MCP utilisés

- `get_runtime_status`
- `discover_devices`
- `discover_wireless_devices`
- `list_known_devices`

## Résultat attendu

Une liste d'appareils, chacun avec :
- `device_id` : identifiant stable à conserver pour les opérations ultérieures.
- `transport` : type de connexion (usb, serial, bluetooth, network, adb, ios, simulator).
- `name` : nom lisible.
- `fingerprint` : empreinte matérielle stable.
- `interfaces` : liste des interfaces exposées (id, kind, etc.).

## Gestion des erreurs

| Situation | Action |
|-----------|--------|
| Aucun appareil trouvé | Vérifier que le matériel est branché et que l'adaptateur correspondant est installé. Relancer `discover_devices`. |
| Dépendance manquante (`ImportError`) | Vérifier `get_runtime_status` pour voir quel adaptateur échoue. Installer l'extra Python correspondant. |
| Erreur de permission OS | Le système d'exploitation bloque l'accès. Vérifier les paramètres de confidentialité (caméra, micro, Bluetooth, USB). |

## Considérations de sécurité

- Cette opération est en lecture seule. Elle ne modifie aucun matériel.
- Aucun appareil n'est activé automatiquement.
- Les résultats sont enregistrés en base locale uniquement si vous appelez explicitement `remember_discovery`.
