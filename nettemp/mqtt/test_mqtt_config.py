#!/usr/bin/env python3
"""
Quick test to verify MQTT config exclude_topics are loaded correctly
Run this to check if your config.conf has the exclude_topics properly set
"""

import sys
import yaml

def test_config(config_file='config.conf'):
    """Test if config file has exclude_topics (optional)"""
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        print(f"✅ Successfully loaded {config_file}")
        print("\nChecking MQTT configuration...")
        
        if 'mqtt' not in config:
            print("❌ No 'mqtt' section found in config!")
            return False
        
        mqtt_config = config['mqtt']
        print(f"✅ Found mqtt section")
        
        if 'exclude_topics' not in mqtt_config:
            print("ℹ No 'exclude_topics' found in mqtt section (this is OK).")
            print("  Nettemp Client will use defaults from mqtt_rules.yaml (if present).")
            return True
        
        exclude_topics = mqtt_config['exclude_topics']
        if isinstance(exclude_topics, str):
            exclude_topics = [exclude_topics]
        
        print(f"✅ Found {len(exclude_topics)} exclude patterns:")
        for pattern in exclude_topics:
            print(f"   - {pattern}")
        
        # Check for common patterns
        required = ['*/LWT', '*/lwt']
        missing = []
        for req in required:
            found = any(req in p or req == p for p in exclude_topics)
            if not found:
                missing.append(req)
        
        if missing:
            print(f"\n⚠️  Recommended patterns missing: {', '.join(missing)}")
        else:
            print("\n✅ All recommended patterns present!")
        
        return True
        
    except FileNotFoundError:
        print(f"❌ Config file not found: {config_file}")
        return False
    except yaml.YAMLError as e:
        print(f"❌ YAML parse error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == '__main__':
    config_file = sys.argv[1] if len(sys.argv) > 1 else 'config.conf'
    print(f"Testing MQTT config in: {config_file}\n")
    success = test_config(config_file)
    sys.exit(0 if success else 1)
