#!/usr/bin/env python3
"""
Startup script for DocuPilot services
Run this to start all required services for the complete system
"""

import subprocess
import sys
import time
import os
from pathlib import Path

def start_service(name, command, cwd=None):
    """Start a service in the background"""
    print(f"🚀 Starting {name}...")
    try:
        process = subprocess.Popen(
            command,
            shell=True,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        time.sleep(2)  # Give service time to start
        
        # Check if process is still running
        if process.poll() is None:
            print(f"✅ {name} started successfully (PID: {process.pid})")
            return process
        else:
            stdout, stderr = process.communicate()
            print(f"❌ {name} failed to start:")
            print(f"   stdout: {stdout.decode()}")
            print(f"   stderr: {stderr.decode()}")
            return None
    except Exception as e:
        print(f"❌ Error starting {name}: {e}")
        return None

def main():
    print("🏦 DocuPilot System Startup")
    print("=" * 50)
    
    services = []
    
    # Start Eligibility Agent
    eligibility_process = start_service(
        "Eligibility Agent",
        "python -m uvicorn agents.eligibility_agent.main:app --host 0.0.0.0 --port 8000 --reload"
    )
    if eligibility_process:
        services.append(("Eligibility Agent", eligibility_process))
    
    # Start Communication Agent
    communication_process = start_service(
        "Communication Agent", 
        "python -m uvicorn agents.communication_agent.main:app --host 0.0.0.0 --port 8001 --reload"
    )
    if communication_process:
        services.append(("Communication Agent", communication_process))
    
    # Start Orchestration Service
    orchestration_process = start_service(
        "Orchestration Service",
        "python -m uvicorn agents.orchestration.main:app --host 0.0.0.0 --port 8002 --reload"
    )
    if orchestration_process:
        services.append(("Orchestration Service", orchestration_process))
    
    # Start Verification Agent
    verification_process = start_service(
        "Verification Agent",
        "python -m uvicorn agents.verification_agent.main:app --host 0.0.0.0 --port 8003 --reload"
    )
    if verification_process:
        services.append(("Verification Agent", verification_process))
    
    # Start Compliance Agent
    compliance_process = start_service(
        "Compliance Agent",
        "python -m uvicorn agents.compliance_agent.main:app --host 0.0.0.0 --port 8003 --reload"
    )
    if compliance_process:
        services.append(("Compliance Agent", compliance_process))
    
    print("\n🎯 Service Status Summary:")
    print("-" * 30)
    for name, process in services:
        status = "✅ Running" if process.poll() is None else "❌ Stopped"
        print(f"{name}: {status}")
    
    print(f"\n📊 Total Services Running: {len(services)}/5")
    
    if len(services) == 5:
        print("\n🎉 All services started successfully!")
        print("\nNext steps:")
        print("1. Run: streamlit run loan_docu_pilot_app.py")
        print("2. Run: streamlit run loan_officer_dashboard.py --server.port 8501")
        print("\n🌐 Service URLs:")
        print("   - Eligibility Agent: http://localhost:8000/docs")
        print("   - Communication Agent: http://localhost:8001/docs")
        print("   - Orchestration Service: http://localhost:8002/docs")
        print("   - Verification Agent: http://localhost:8003/docs")
        print("   - Compliance Agent: http://localhost:8003/docs")
    else:
        print("\n⚠️  Some services failed to start. Check the error messages above.")
    
    print("\n💡 Press Ctrl+C to stop all services")
    
    try:
        # Keep script running
        while True:
            time.sleep(10)
            # Check if any service has stopped
            for name, process in services[:]:
                if process.poll() is not None:
                    print(f"⚠️  {name} has stopped unexpectedly")
                    services.remove((name, process))
    except KeyboardInterrupt:
        print("\n🛑 Stopping all services...")
        for name, process in services:
            try:
                process.terminate()
                process.wait(timeout=5)
                print(f"✅ Stopped {name}")
            except subprocess.TimeoutExpired:
                process.kill()
                print(f"🔥 Force killed {name}")
            except Exception as e:
                print(f"❌ Error stopping {name}: {e}")
        
        print("👋 All services stopped. Goodbye!")

if __name__ == "__main__":
    main()