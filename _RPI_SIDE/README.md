📂 robot_project/
├── 📁 core/                # Noyau du projet : abstraction et gestion des modules
│   ├── __init__.py         # Permet de traiter le dossier comme un package
│   ├── tcp_server.py       # Classe abstraite pour le serveur TCP
│   ├── uart_manager.py     # Classe abstraite pour la gestion de l'UART
│   ├── hotspot_manager.py  # Module pour la gestion du hotspot
│   └── logger.py           # Configuration du logger global
├── 📁 modules/             # Modules concrets spécifiques
│   ├── __init__.py         # Permet de traiter le dossier comme un package
│   ├── my_tcp_server.py    # Implémentation concrète de la classe `TcpServer`
│   ├── my_uart_driver.py   # Implémentation concrète de la classe `UartManager`
│   └── hotspot_monitor.py  # Gestion des fonctionnalités avancées du hotspot
├── 📁 configs/             # Configuration et fichiers constants
│   ├── settings.py         # Variables globales de configuration
│   └── secrets.py          # (Optionnel) Gestion des clés API ou secrets
├── 📁 logs/                # Dossier pour les fichiers de log
│   └── robot.log           # Log principal du programme
├── main.py                 # Point d'entrée principal du programme
└── README.md               # Documentation pour comprendre et démarrer avec le projet
