#!/usr/bin/env python3
"""
Advanced System Monitoring Script
Provides comprehensive system metrics for the dashboard
"""
import json
import sys
import time
import os
import platform
import socket
import subprocess
try:
    import psutil
except ImportError:
    print(json.dumps({
        "success": False,
        "message": "psutil module not installed. Please install with 'pip install psutil'",
        "error": "DependencyError"
    }))
    sys.exit(1)

def get_system_info():
    """Get basic system information"""
    try:
        info = {
            "hostname": socket.gethostname(),
            "platform": platform.system(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "boot_time": psutil.boot_time()
        }
        
        # Calculate uptime
        uptime_seconds = time.time() - psutil.boot_time()
        days, remainder = divmod(uptime_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        info["uptime"] = {
            "days": int(days),
            "hours": int(hours),
            "minutes": int(minutes),
            "seconds": int(seconds),
            "total_seconds": uptime_seconds
        }
        
        return info
    except Exception as e:
        return {"error": str(e)}

def get_cpu_info(detail_level="standard"):
    """Get CPU information and usage"""
    try:
        cpu_info = {
            "logical_cores": psutil.cpu_count(),
            "physical_cores": psutil.cpu_count(logical=False),
            "usage": {
                "total_percent": psutil.cpu_percent(interval=0.5),
                "per_core": psutil.cpu_percent(interval=0.5, percpu=True)
            },
            "load_avg": os.getloadavg()
        }
        
        # Add frequency info if available
        try:
            freq = psutil.cpu_freq()
            if freq:
                cpu_info["frequency"] = {
                    "current": freq.current,
                    "min": freq.min,
                    "max": freq.max
                }
        except:
            pass
        
        # Add CPU temperature if available and detail level is full
        if detail_level == "full":
            try:
                temp_info = psutil.sensors_temperatures()
                if temp_info:
                    cpu_info["temperature"] = temp_info
            except:
                pass
                
            # Add CPU times if detail level is full
            try:
                cpu_times = psutil.cpu_times_percent()
                cpu_info["times"] = {
                    "user": cpu_times.user,
                    "system": cpu_times.system,
                    "idle": cpu_times.idle
                }
            except:
                pass
                
        return cpu_info
    except Exception as e:
        return {"error": str(e)}

def get_memory_info():
    """Get memory usage information"""
    try:
        # Virtual memory
        virtual = psutil.virtual_memory()
        memory_info = {
            "total": virtual.total,
            "available": virtual.available,
            "used": virtual.used,
            "free": virtual.free,
            "percent": virtual.percent
        }
        
        # Swap memory
        swap = psutil.swap_memory()
        memory_info["swap"] = {
            "total": swap.total,
            "used": swap.used,
            "free": swap.free,
            "percent": swap.percent
        }
        
        return memory_info
    except Exception as e:
        return {"error": str(e)}

def get_disk_info(detail_level="standard"):
    """Get disk usage information"""
    try:
        # Overall disk usage
        partitions = psutil.disk_partitions()
        disk_info = {"partitions": []}
        
        for partition in partitions:
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                partition_info = {
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "fstype": partition.fstype,
                    "opts": partition.opts,
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": usage.percent
                }
                disk_info["partitions"].append(partition_info)
            except PermissionError:
                # Skip partitions that can't be accessed
                continue
        
        # Add I/O statistics if detail level is standard or full
        if detail_level in ["standard", "full"]:
            try:
                io_counters = psutil.disk_io_counters(perdisk=True)
                disk_info["io"] = {}
                
                for disk, counters in io_counters.items():
                    disk_info["io"][disk] = {
                        "read_count": counters.read_count,
                        "write_count": counters.write_count,
                        "read_bytes": counters.read_bytes,
                        "write_bytes": counters.write_bytes,
                        "read_time": counters.read_time,
                        "write_time": counters.write_time
                    }
            except:
                pass
                
        return disk_info
    except Exception as e:
        return {"error": str(e)}

def get_network_info(detail_level="standard"):
    """Get network interface information"""
    try:
        # Get network interface addresses
        network_info = {"interfaces": {}}
        
        for interface_name, interface_addresses in psutil.net_if_addrs().items():
            addresses = []
            for addr in interface_addresses:
                address_info = {
                    "family": str(addr.family),
                    "address": addr.address,
                    "netmask": addr.netmask,
                    "broadcast": addr.broadcast
                }
                addresses.append(address_info)
            
            # Get interface statistics
            if_stats = psutil.net_if_stats().get(interface_name)
            if if_stats:
                network_info["interfaces"][interface_name] = {
                    "addresses": addresses,
                    "stats": {
                        "isup": if_stats.isup,
                        "duplex": str(if_stats.duplex),
                        "speed": if_stats.speed,
                        "mtu": if_stats.mtu
                    }
                }
            else:
                network_info["interfaces"][interface_name] = {
                    "addresses": addresses
                }
        
        # Add IO counters
        io_counters = psutil.net_io_counters(pernic=True)
        for interface_name, counters in io_counters.items():
            if interface_name in network_info["interfaces"]:
                network_info["interfaces"][interface_name]["counters"] = {
                    "bytes_sent": counters.bytes_sent,
                    "bytes_recv": counters.bytes_recv,
                    "packets_sent": counters.packets_sent,
                    "packets_recv": counters.packets_recv,
                    "errin": counters.errin,
                    "errout": counters.errout,
                    "dropin": counters.dropin,
                    "dropout": counters.dropout
                }
        
        # Add active connections if detail level is full
        if detail_level == "full":
            try:
                connections = psutil.net_connections()
                network_info["connections"] = []
                
                for conn in connections:
                    try:
                        connection_info = {
                            "fd": conn.fd,
                            "family": conn.family,
                            "type": conn.type,
                            "laddr": {
                                "ip": conn.laddr.ip if conn.laddr else None,
                                "port": conn.laddr.port if conn.laddr else None
                            },
                            "raddr": {
                                "ip": conn.raddr.ip if conn.raddr else None,
                                "port": conn.raddr.port if conn.raddr else None
                            },
                            "status": conn.status,
                            "pid": conn.pid
                        }
                        network_info["connections"].append(connection_info)
                    except:
                        # Skip connections that can't be fully processed
                        pass
            except:
                pass
                
        return network_info
    except Exception as e:
        return {"error": str(e)}

def get_process_info(detail_level="standard"):
    """Get information about running processes"""
    try:
        process_info = {"count": 0, "processes": []}
        
        for proc in psutil.process_iter(['pid', 'name', 'username', 'status', 'cpu_percent', 'memory_percent']):
            try:
                # Basic process info for all detail levels
                pinfo = proc.info
                
                # Add more information for standard and full detail levels
                if detail_level in ["standard", "full"]:
                    pinfo.update({
                        "created": proc.create_time(),
                        "memory_info": {
                            "rss": proc.memory_info().rss,
                            "vms": proc.memory_info().vms
                        },
                        "num_threads": proc.num_threads()
                    })
                
                # Add even more detailed info for full detail level
                if detail_level == "full":
                    try:
                        pinfo.update({
                            "exe": proc.exe(),
                            "cmdline": proc.cmdline(),
                            "cwd": proc.cwd(),
                            "open_files": [f.path for f in proc.open_files()],
                            "connections": [
                                {
                                    "fd": c.fd,
                                    "family": c.family,
                                    "type": c.type,
                                    "laddr": {
                                        "ip": c.laddr.ip if c.laddr else None,
                                        "port": c.laddr.port if c.laddr else None
                                    },
                                    "raddr": {
                                        "ip": c.raddr.ip if c.raddr else None,
                                        "port": c.raddr.port if c.raddr else None
                                    },
                                    "status": c.status
                                }
                                for c in proc.connections()
                            ]
                        })
                    except (psutil.AccessDenied, psutil.ZombieProcess):
                        # Skip detailed info for processes we can't access
                        pass
                
                process_info["processes"].append(pinfo)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # Skip processes that disappeared or can't be accessed
                pass
        
        process_info["count"] = len(process_info["processes"])
        
        # Sort processes by CPU usage (most intensive first)
        process_info["processes"].sort(key=lambda x: x.get("cpu_percent", 0), reverse=True)
        
        # Limit the number of processes returned to avoid too much data
        if detail_level == "basic":
            limit = 10
        elif detail_level == "standard":
            limit = 25
        else:  # full
            limit = 50
            
        process_info["processes"] = process_info["processes"][:limit]
        
        return process_info
    except Exception as e:
        return {"error": str(e)}

def main():
    """Main function to handle script execution."""
    # Default values
    detail_level = "standard"  # 'basic', 'standard', or 'full'
    component = "all"  # 'cpu', 'memory', 'disk', 'network', 'processes', or 'all'
    
    # Check if we have input on stdin
    try:
        if not sys.stdin.isatty():
            input_data = json.load(sys.stdin)
            detail_level = input_data.get("detail_level", detail_level)
            component = input_data.get("component", component)
    except json.JSONDecodeError:
        # If JSON parsing fails, use default values
        pass
    except Exception as e:
        print(json.dumps({
            "success": False,
            "message": f"Error processing input: {str(e)}",
            "error": str(e)
        }))
        sys.exit(1)
    
    # Validate detail level
    if detail_level not in ["basic", "standard", "full"]:
        detail_level = "standard"
    
    try:
        result = {
            "success": True,
            "message": f"System information retrieved with {detail_level} detail level",
            "timestamp": time.time(),
            "data": {}
        }
        
        # System info is always included
        result["data"]["system"] = get_system_info()
        
        # Add requested components
        if component in ["all", "cpu"]:
            result["data"]["cpu"] = get_cpu_info(detail_level)
        
        if component in ["all", "memory"]:
            result["data"]["memory"] = get_memory_info()
        
        if component in ["all", "disk"]:
            result["data"]["disk"] = get_disk_info(detail_level)
        
        if component in ["all", "network"]:
            result["data"]["network"] = get_network_info(detail_level)
        
        if component in ["all", "processes"]:
            result["data"]["processes"] = get_process_info(detail_level)
        
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({
            "success": False,
            "message": f"Error collecting system information: {str(e)}",
            "error": str(e)
        }))

if __name__ == "__main__":
    main()