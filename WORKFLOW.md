# Workflow Universal Device MCP pour agents IA

Ce document est une couche d'instructions réutilisable entre un agent IA et le serveur **Universal Device MCP**. Il est indépendant de toute plateforme (Agensi, Claude, OpenAI, etc.) et ne dépend d'aucun marketplace spécifique.

## Objectif

Permettre à un agent IA de :
1. Découvrir le matériel connecté à l'ordinateur hôte.
2. Inspecter les interfaces et capacités de chaque appareil.
3. Exécuter des opérations de manière sécurisée, en respectant les politiques d'accès locales.
4. Vérifier que les opérations ont réussi.
5. Gérer les erreurs, les appareils indisponibles et les opérations non supportées.

## Quand utiliser Universal Device MCP

Utilisez ce serveur lorsque vous devez :
- Découvrir du matériel local (USB, série, Bluetooth, réseau mDNS, Android ADB, iOS).
- Lire ou écrire sur des interfaces matérielles de manière générique.
- Conserver un inventaire persistant des appareils découverts entre sessions.
- Exécuter des opérations sur plusieurs appareils simultanément (lectures indépendantes).
- Contrôler des appareils simulés pour des tests sans matériel physique.

**N'utilisez pas ce serveur pour :**
- Contrôler du matériel dont le protocole est inconnu et non documenté (le serveur ne devine pas les formats propriétaires).
- Flasher un firmware, formater un périphérique, exécuter du code arbitraire ou effectuer une réinitialisation d'usine (bloqués dans tous les modes d'accès).
- Accéder à du matériel sans les permissions du système d'exploitation (Windows, macOS, Linux restent autorité).

## 1. Découverte des appareils

### Étape 1 — Vérifier l'état du serveur

Avant toute découverte, vérifiez que le serveur fonctionne et que les adaptateurs sont disponibles.

**Outil :** `get_runtime_status`

Ce que vous obtenez :
- Version Python et plateforme OS.
- État de chaque adaptateur (USB, HID, Serial, Bluetooth, Network, iOS, ADB).
- Chemin de la base de données locale.
- Erreurs de chargement de plugins éventuelles.

### Étape 2 — Découvrir les appareils locaux

**Outil :** `discover_devices`

Vous pouvez filtrer par transport (ex: `transports=["usb"]`, `transports=["bluetooth"]`, `transports=["serial"]`).

Résultat : une liste d'appareils avec `device_id`, `transport`, `name`, `fingerprint`, `identity`, `hardware`, `interfaces`.

### Étape 3 — Découvrir les appareils sans fil (optionnel)

**Outil :** `discover_wireless_devices`

Découvre les services BLE, mDNS, Android ADB et iOS mobdev2 annoncés localement.

### Étape 4 — Lister les appareils déjà connus

**Outil :** `list_known_devices`

Retourne les profils enregistrés dans la base de données locale SQLite.

## 2. Inspection des capacités d'un appareil

### Étape 1 — Inspecter un appareil spécifique

**Outil :** `inspect_device(device_id)`

Nécessite un `device_id` exact obtenu lors de la découverte.

Résultat : profil complet avec interfaces, état de connexion et métadonnées.

### Étape 2 — Comprendre une interface

**Outil :** `explain_device_interface(device_id, interface_id)`

Donne une description lisible de ce que fait une interface et quelles opérations elle supporte.

### Étape 3 — Voir les capacités globales

**Outil :** `get_device_capabilities(device_id)`

Résumé des capacités de l'appareil.

### Étape 4 — Voir les protocoles supportés

**Outil :** `get_supported_protocols()`

Liste des protocoles et transports supportés par le serveur.

## 3. Sélection de l'outil MCP approprié

Utilisez ce tableau pour choisir l'outil selon votre objectif :

| Objectif | Outil MCP | Lecture / Écriture |
|----------|-----------|---------------------|
| Découvrir le matériel local | `discover_devices` | Lecture |
| Découvrir le matériel sans fil | `discover_wireless_devices` | Lecture |
| Lister les appareils connus | `list_known_devices` | Lecture |
| Voir l'état du serveur | `get_runtime_status` | Lecture |
| Inspecter un appareil | `inspect_device` | Lecture |
| Comprendre une interface | `explain_device_interface` | Lecture |
| Capacités d'un appareil | `get_device_capabilities` | Lecture |
| Protocoles supportés | `get_supported_protocols` | Lecture |
| Communiquer génériquement | `communicate_device` | Lecture ou écriture |
| Plusieurs lectures simultanées | `communicate_many` | Lecture |
| Ouvrir une interface persistante | `open_interface` | Écriture (session) |
| Fermer une interface | `close_interface` | Écriture (session) |
| Lire des événements | `get_device_events` | Lecture |
| Voir la politique d'accès | `get_access_policy` | Lecture |
| Recharger la politique | `reload_access_policy` | Lecture |
| Connecter un appareil | `connect_device` | Écriture (état) |
| Déconnecter un appareil | `disconnect_device` | Écriture (état) |
| Supprimer une expérience | `delete_device_experiment` | Écriture (historique) |
| Caméra : découverte | `discover_cameras` | Lecture |
| Caméra : capture | `capture_camera_image` | Écriture (mémoire) |
| Micro : découverte | `discover_microphones` | Lecture |
| Micro : enregistrement | `record_audio_sample` | Écriture (mémoire) |
| Groupe : créer | `create_device_group` | Écriture (mémoire) |
| Groupe : lire | `read_device_group` | Lecture |
| Groupe : préparation écriture | `prepare_group_write` | Écriture (plan) |
| Groupe : exécution approuvée | `execute_approved_group_write` | Écriture (nécessite approbation humaine) |
| Groupe : supprimer | `delete_device_group` | Écriture (mémoire) |
| Rappeler une découverte | `remember_discovery` | Écriture (mémoire) |
| Mettre à jour un profil | `update_device_profile` | Écriture (mémoire) |
| Voir la connaissance | `get_device_knowledge` | Lecture |
| Exporter un profil | `export_device_profile` | Lecture |
| Oublier un appareil | `forget_device` | Écriture (suppression) |
| Analyser une charge utile | `analyze_payload` | Lecture |
| Générer un rapport | `generate_device_report` | Lecture |
| Diagnostics | `run_device_diagnostics` | Lecture |
| Démarrer le moniteur | `start_device_monitor` | Écriture (surveillance) |
| Arrêter le moniteur | `stop_device_monitor` | Écriture (surveillance) |

## 4. Exécution sécurisée d'une opération

### Règle d'or : jamais d'hypothèse

Avant d'appeler un outil d'écriture :
1. Vérifiez que l'appareil existe et est connecté (`inspect_device`, champ `connected`).
2. Vérifiez que l'interface existe (`interfaces` dans le résultat d'inspection).
3. Lisez la politique d'accès (`get_access_policy`) pour connaître le mode (`safe`, `trusted`, `full`) et les règles autorisées.
4. Lisez la description de l'interface (`explain_device_interface`).

### Modes d'accès

Le mode est défini localement par le propriétaire de l'ordinateur via la variable d'environnement `UDMCP_ACCESS_MODE`. Un agent IA **ne peut pas le changer**.

| Mode | Comportement |
|------|-------------|
| `safe` (défaut) | Lectures autorisées. Écritures bloquées sans règle exacte (transport, device_id, interface_id, opération). |
| `trusted` | Lectures, ouvertures et écritures autorisées pour les appareils dont l'ID/empreinte figure dans `trusted_devices` de la politique locale. |
| `full` | Opérations non critiques sans règle par opération, mais limites de taille, refus explicites, audit et blocages d'opérations critiques conservés. |

### Opérations bloquées dans tous les modes

Ces opérations sont toujours refusées, quel que soit le mode :
- `flash`, `firmware_update`, `erase`, `wipe`, `format`, `delete`, `remove`, `factory_reset`, `bootloader_unlock`, `execute`.

### Limites de taille

- Écriture unique : `max_write_bytes` (défaut 4096 octets, configurable dans la politique).
- Groupe écriture : 32 cibles maximum, 4096 octets maximum.

### Confirmation explicite pour les écritures de groupe

`prepare_group_write` crée un plan gelé. `execute_approved_group_write` nécessite une approbation humaine via l'élicitation MCP. Un agent IA ne peut pas exécuter une écriture de groupe sans cette approbation.

### Médias (caméra / microphone)

Nécessitent `UDMCP_MEDIA_CAPTURE=true` (opt-in du propriétaire). Rien n'est activé automatiquement. Les captures sont en mémoire, non écrites sur disque.

## 5. Vérification du succès d'une opération

Après chaque appel d'outil :

1. Vérifiez que le résultat n'est pas une erreur (champ `error` ou exception levée).
2. Pour une écriture : vérifiez que le résultat indique `success: true` ou l'équivalent selon l'outil.
3. Pour une lecture : vérifiez que les données retournées sont cohérentes avec la demande.
4. Pour une opération de groupe : vérifiez les résultats par cible (chaque cible a son propre résultat, les échecs partiels sont possibles).
5. Ne jamais déclarer une opération réussie sans preuve dans le résultat de l'outil.

## 6. Gestion des erreurs

### Types d'erreurs courants

| Situation | Cause probable | Action |
|-----------|---------------|--------|
| `KeyError: Unknown device` | `device_id` inexistant ou appareil oublié | Relancer `discover_devices` |
| `PermissionError` | Politique `safe` sans règle exacte, ou mode restreint | Demander à l'utilisateur de configurer la politique locale |
| `RuntimeError: not currently connected` | Appareil non connecté | Appeler `connect_device` d'abord |
| `TimeoutError` | Opération matérielle bloquée | Réessayer avec un timeout plus court ou abandonner |
| `ImportError` | Dépendance optionnelle manquante (ex: `usb`, `hid`) | Installer l'extra correspondant |
| `ValueError` | Paramètre invalide (ex: durée audio hors limites) | Corriger les paramètres selon la doc de l'outil |

### Appareil indisponible

Si un appareil ne répond pas :
1. Vérifiez son état de connexion (`inspect_device`).
2. Essayez `disconnect_device` puis `connect_device`.
3. Si l'appareil physique est débranché, relancez `discover_devices`.
4. Ne considérez jamais un appareil déconnecté comme définitivement perdu sans nouvelle découverte.

## 7. Communication des résultats à l'utilisateur

- Présentez clairement le `device_id`, le `transport` et le `name` de chaque appareil concerné.
- Distinguez les succès des échecs par cible (surtout pour `communicate_many` et les groupes).
- Indiquez si une opération a été bloquée par la politique d'accès.
- Ne jamais inventer d'informations sur un appareil. Si le serveur ne retourne pas une propriété, indiquez qu'elle est inconnue.
- Pour les captures média : indiquez que l'image/son est en mémoire, non persistante, et donnez le format MIME.

## Limites connues

- Le serveur est une couche d'accès générique, pas une garantie que tout matériel est contrôlable.
- Les protocoles propriétaires non documentés restent des expériences jusqu'à validation.
- Certaines opérations (flash, wipe, format, execute) sont bloquées dans tous les modes d'accès.
- L'IA ne peut pas changer le mode d'accès (`safe`/`trusted`/`full`) — c'est réservé au propriétaire local.
- Les captures caméra/audio sont limitées (une image JPEG ≤ 900 Ko, ≤ 10 s de WAV mono 16 kHz, pas de flux continu).
- Les écritures de groupe nécessitent une approbation humaine explicite via MCP elicitation.
