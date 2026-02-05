#!/bin/bash
echo "🔧 Fixing execution permissions for all .sh scripts..."
find . -type f -name "*.sh" -exec chmod 755 {} \;
echo "✔️ Done!"
