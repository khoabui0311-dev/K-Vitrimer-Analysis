import matplotlib.pyplot as plt
import numpy as np
import io
import pandas as pd

class PublicationToolkit:
    def __init__(self):
        self.params = {
            'font.family': 'sans-serif',
            'font.size': 10,
            'axes.linewidth': 1.5,
            'xtick.direction': 'in',
            'ytick.direction': 'in',
            'legend.frameon': False
        }

    def _apply_style(self, style_name="Classic"):
        plt.rcParams.update(self.params)
        if "Classic" in style_name:
            plt.rcParams['xtick.top'] = True
            plt.rcParams['ytick.right'] = True
            plt.rcParams['axes.grid'] = False
        else:
            plt.rcParams['xtick.top'] = False
            plt.rcParams['ytick.right'] = False
            plt.rcParams['axes.grid'] = True

    def generate_relaxation_plot(self, results, width=3.5, height=3.0, style="Classic", x_scale="log"):
        """Plots list of results (Pre-filtered by user selection)."""
        self._apply_style(style)
        fig, ax = plt.subplots(figsize=(width, height))
        
        # Color cycle
        colors = plt.cm.jet(np.linspace(0, 1, len(results)))

        for i, res in enumerate(results):
            t = np.array(res['Raw']['t'])
            g = np.array(res['Raw']['g'])
            temp = res['Temp']
            
            # Decimate
            step = max(1, len(t) // 200)
            ax.plot(t[::step], g[::step], 'o', color=colors[i], markersize=3, alpha=0.6, label=f"{temp} °C")
            
            best = res.get('Best_Model')
            if best and best in res['Fits']:
                fit = res['Fits'][best]['curve']
                if len(fit) == len(t):
                    # Dashed Black Fit Line
                    ax.plot(t, fit, 'k--', linewidth=1.0, alpha=0.8)

        # Apply Scale
        ax.set_xscale(x_scale)

        ax.set_xlabel("Time (s)", fontweight='bold')
        ax.set_ylabel(r"$G(t)/G_0$", fontweight='bold')
        ax.set_ylim(-0.1, 1.1)
        
        # Smaller Legend Font
        ax.legend(fontsize=6, frameon=False, loc='best')
        
        plt.tight_layout()
        return fig

    def generate_arrhenius_plot(self, kinetics_df, width=3.5, height=3.0, style="Classic"):
        """
        Accepts the 'kinetics_df' from the GUI.
        """
        self._apply_style(style)
        fig, ax = plt.subplots(figsize=(width, height))
        
        if kinetics_df is None or kinetics_df.empty:
            return fig
            
        df = kinetics_df[kinetics_df['Include'] == True]
        
        if df.empty:
            return fig

        for name, group in df.groupby("Type"):
            color = 'navy' if 'Fast' in name or 'Main' in name else 'firebrick'
            
            ax.plot(group['1000/T'], group['ln(Tau)'], 'o', color=color, markersize=5, label=f"{name}")
            
            if len(group) >= 3:
                from scipy.stats import linregress
                slope, intercept, r_val, _, _ = linregress(group['1000/T'], group['ln(Tau)'])
                Ea = slope * 8.314462
                r2 = r_val**2
                
                xr = np.linspace(group['1000/T'].min()*0.95, group['1000/T'].max()*1.05, 10)
                yr = slope * xr + intercept
                
                # Dashed line with R2 in label
                ax.plot(xr, yr, '--', color=color, linewidth=1.2, label=f"$E_a$={Ea:.1f} kJ ($R^2$={r2:.3f})")

        ax.set_xlabel(r"$1000 / T$ (K$^{-1}$)", fontweight='bold')
        ax.set_ylabel(r"ln($\tau$)", fontweight='bold')
        
        # Smaller Legend Font
        ax.legend(fontsize=6, frameon=False)
        
        plt.tight_layout()
        return fig

    def save_to_buffer(self, fig, format='png', dpi=300):
        buf = io.BytesIO()
        fig.savefig(buf, format=format, dpi=dpi, bbox_inches='tight')
        buf.seek(0)
        return buf