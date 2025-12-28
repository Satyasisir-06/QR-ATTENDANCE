# Quick Setup Script for Local Development

Write-Output "Installing required packages..."
pip install -r requirements.txt

Write-Output "`n✅ Setup complete!"
Write-Output "`nTo run the application:"
Write-Output "  python app1.py"
Write-Output "`nThe app will run at: http://localhost:5000"
Write-Output "`nDefault credentials:"
Write-Output "  Admin: admin / admin123"
Write-Output "  Student: student / student123"
