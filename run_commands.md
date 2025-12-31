dotenv run -- ray start --head

serve deploy advanced_web_research.query:fast_app 

koco start --register http://localhost:8000/-/routes



Created scripts/local-test.sh. Usage:

  # Start all services
  ./scripts/local-test.sh start

  # Stop all services
  ./scripts/local-test.sh stop

  # Restart all services
  ./scripts/local-test.sh restart

  # Check status
  ./scripts/local-test.sh status

  The script:
  - Loads environment variables from .env
  - Activates the virtual environment
  - Starts Ray, deploys Serve, and starts Koco
  - Provides helpful status output

  UI will be available at http://localhost:3370

