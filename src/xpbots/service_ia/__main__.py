"""Point d'entrée autonome du service partagé, sans import de courtier."""
from .c4_service import main

if __name__=='__main__':raise SystemExit(main())
