#!/usr/bin/env python
"""
Script to run the complete routing analysis pipeline.
Allows user to select a topography file and processes it end-to-end.
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime
import xarray as xr
import numpy as np

from routing import run_routines


def select_file_interactive(start_dir=None):
    """
    Interactively prompt user to select a topography file.
    
    Parameters
    ----------
    start_dir : str, optional
        Starting directory for file selection
        
    Returns
    -------
    Path
        Path to the selected file
    """
    if start_dir is None:
        start_dir = Path.cwd()
    else:
        start_dir = Path(start_dir)
    
    print(f"\nStarting directory: {start_dir}")
    print("\nAvailable NetCDF files:")
    
    # Find all NetCDF files
    nc_files = list(start_dir.glob("*.nc")) + list(start_dir.glob("**/*.nc"))
    nc_files = list(set(nc_files))  # Remove duplicates
    nc_files.sort()
    
    if not nc_files:
        print("No NetCDF files found!")
        return None
    
    for i, file in enumerate(nc_files, 1):
        print(f"  {i}. {file}")
    
    while True:
        try:
            choice = input(f"\nSelect file (1-{len(nc_files)}): ").strip()
            index = int(choice) - 1
            if 0 <= index < len(nc_files):
                return nc_files[index]
            else:
                print(f"Please enter a number between 1 and {len(nc_files)}")
        except ValueError:
            print("Invalid input. Please enter a number.")


def load_topography_file(filepath):
    """
    Load topography and latitude data from a NetCDF file.
    
    Parameters
    ----------
    filepath : str or Path
        Path to the topography NetCDF file
        
    Returns
    -------
    tuple
        (topo, latitudes) arrays
        
    Raises
    ------
    FileNotFoundError
        If file doesn't exist
    ValueError
        If required variables are not found
    """
    filepath = Path(filepath)
    
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    
    print(f"\nLoading file: {filepath}")
    ds = xr.open_dataset(filepath)
    
    # Try to find topography variable
    topo_names = ["topo", "topography", "elevation", "dem", "height"]
    topo = None
    for name in topo_names:
        if name in ds.data_vars:
            topo = ds[name].values
            print(f"Found topography variable: {name}")
            break
    
    if topo is None:
        # If not found, list available variables
        print("\nAvailable variables:")
        for var in ds.data_vars:
            print(f"  - {var}: {ds[var].shape}")
        raise ValueError(
            f"Could not find topography variable. Tried: {topo_names}\n"
            "Please specify the topography variable name."
        )
    
    # Try to find latitude variable
    lat_names = ["lat", "latitude", "nav_lat"]
    latitudes = None
    for name in lat_names:
        if name in ds.coords:
            latitudes = ds[name].values
            print(f"Found latitude coordinate: {name}")
            break
        elif name in ds.data_vars:
            latitudes = ds[name].values
            print(f"Found latitude variable: {name}")
            break
    
    if latitudes is None:
        # If not found, try to infer from topo dimensions
        print("Could not find latitude coordinate, inferring from topo shape...")
        latitudes = np.arange(89.5, -90.5, -1)[:topo.shape[0]]
        if len(latitudes) != topo.shape[0]:
            raise ValueError(
                f"Could not match latitude array to topography dimensions. "
                f"Topo shape: {topo.shape}, Latitude length needed: {topo.shape[0]}"
            )
    
    # Flatten latitude if it's 2D
    if latitudes.ndim == 2:
        latitudes = latitudes[:, 0]
    
    print(f"Topography shape: {topo.shape}")
    print(f"Latitude range: {latitudes.min():.2f} to {latitudes.max():.2f}")
    
    return topo, latitudes


def load_custom_orca(filepath=None):
    """
    Load custom ORCA grid file if available.
    
    Parameters
    ----------
    filepath : str or Path, optional
        Path to ORCA grid file
        
    Returns
    -------
    xarray.Dataset or None
        ORCA grid dataset or None if not provided/found
    """
    if filepath is None:
        return None
    
    filepath = Path(filepath)
    if not filepath.exists():
        print(f"Warning: ORCA file not found: {filepath}")
        return None
    
    print(f"\nLoading ORCA grid: {filepath}")
    return xr.open_dataset(filepath)


def save_outputs(ds_routing, ds_bathy, ds_soils, ds_topo_high_res, output_dir=None):
    """
    Save output datasets to NetCDF files.
    
    Parameters
    ----------
    ds_routing : xarray.Dataset
        Routing dataset
    ds_bathy : xarray.Dataset
        Bathymetry dataset
    ds_soils : xarray.Dataset
        Soils dataset
    ds_topo_high_res : xarray.Dataset
        High-resolution topography dataset
    output_dir : str or Path, optional
        Output directory. Defaults to current directory.
    """
    if output_dir is None:
        output_dir = Path.cwd()
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    files = {
        "routing.nc": ds_routing,
        "bathymetry.nc": ds_bathy,
        "soils.nc": ds_soils,
        "topo_high_res.nc": ds_topo_high_res,
    }
    
    print(f"\nSaving outputs to: {output_dir}")
    for filename, dataset in files.items():
        filepath = output_dir / filename
        print(f"  Saving {filename}...", end="", flush=True)
        dataset.to_netcdf(filepath)
        print(" ✓")
    
    print(f"\nAll outputs saved successfully!")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Run complete routing analysis pipeline on topography data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_routing.py                              # Interactive file selection
  python run_routing.py -f topography.nc             # Use specific file
  python run_routing.py -f topo.nc -o ./output       # Specify output directory
  python run_routing.py -f topo.nc --orca orca.nc    # Use custom ORCA grid
        """
    )
    
    parser.add_argument(
        "-f", "--file",
        help="Path to topography NetCDF file"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output directory for results (default: current directory)"
    )
    parser.add_argument(
        "--orca",
        help="Path to custom ORCA grid file (optional)"
    )
    
    args = parser.parse_args()
    
    try:
        # Select or load topography file
        if args.file:
            topo_file = Path(args.file)
        else:
            topo_file = select_file_interactive()
            if topo_file is None:
                sys.exit(1)
        
        # Load data
        topo, latitudes = load_topography_file(topo_file)
        
        # Load custom ORCA grid if provided
        custom_orca = load_custom_orca(args.orca)
        
        # Run routing analysis
        print("\n" + "="*60)
        print("Starting Routing Analysis")
        print("="*60)
        start_time = datetime.now()
        
        ds_routing, ds_bathy, ds_soils, ds_topo_high_res = run_routines(
            topo, latitudes, custom_orca=custom_orca
        )
        
        end_time = datetime.now()
        elapsed = end_time - start_time
        print("="*60)
        print(f"Routing Analysis Complete! ({elapsed})")
        print("="*60)
        
        # Save outputs
        save_outputs(
            ds_routing, ds_bathy, ds_soils, ds_topo_high_res,
            output_dir=args.output
        )
        
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
