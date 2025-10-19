#!/bin/bash

echo "UiPath Process Listing Test Setup"
echo "=========================================="

# Activate virtual environment
source .venv/bin/activate

# Check if mcp_servers.db exists
if [ ! -f "mcp_servers.db" ]; then
    echo "Database not found. Creating..."
fi

# Create test user with UiPath config
python -c "
import asyncio
import sys
sys.path.insert(0, 'backend')
from src.database import Database

async def setup():
    db = Database('database/mcp_servers.db')
    await db.initialize()
    
    # Check if testuser exists
    user = await db.get_user_by_username('testuser')
    
    if not user:
        print('Creating test user...')
        user_id = await db.create_user(
            username='testuser',
            email='test@example.com',
            password='password123',
            role='user'
        )
        print(f'✓ Created user: testuser')
    else:
        user_id = user['id']
        print(f'✓ User exists: testuser')
    
    # Prompt for UiPath config
    print('')
    print('Enter UiPath Configuration:')
    print('(Press Ctrl+C to skip)')
    print('')
    
    try:
        url = input('UiPath URL (e.g., https://cloud.uipath.com/account/tenant): ').strip()
        token = input('UiPath PAT: ').strip()
        folder = input('Folder Path (optional, e.g., /Production): ').strip()
        
        if url and token:
            await db.update_user_uipath_config(
                user_id=user_id,
                uipath_url=url,
                uipath_access_token=token,
                uipath_folder_path=folder if folder else None
            )
            print('')
            print('✓ UiPath configuration saved')
            
            # Test the configuration
            print('')
            print('Testing UiPath connection...')
            from src.uipath_client import UiPathClient
            
            client = UiPathClient()
            processes = await client.list_processes(url, token, folder if folder else None)
            
            print(f'✓ Successfully connected! Found {len(processes)} processes')
            
            if processes:
                print('')
                print('Sample processes:')
                for p in processes[:3]:
                    print(f'  - {p[\"name\"]} (v{p[\"version\"]})')
        else:
            print('⚠ Skipped UiPath configuration')
    
    except KeyboardInterrupt:
        print('')
        print('⚠ Skipped UiPath configuration')
    except Exception as e:
        print(f'❌ Error: {e}')
    
    print('')
    print('========================================')
    print('Setup completed!')
    print('')
    print('Login credentials:')
    print('  Username: testuser')
    print('  Password: password123')

asyncio.run(setup())
"

echo ""
echo "You can now start the server and login:"
echo "  cd backend && python -m src.main"
