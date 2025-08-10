def main() -> None:
    import pandas as pd
    import plotly.graph_objects as go
    import threading
    import webbrowser
    import tempfile
    import os

    dfs: dict[str, pd.DataFrame] = {}
    print("csv-mcp server started. Available commands: load_csv <file1> [file2 ...], plot <file1> [file2 ...] <column>, exit, quit")
    while True:
        try:
            command = input("csv-mcp> ").strip()
        except EOFError:
            break
        if not command:
            continue
        if command.startswith("load_csv"):
            parts = command.split()
            if len(parts) < 2:
                print("Usage: load_csv <file1> [file2 ...]")
                continue
            for filename in parts[1:]:
                try:
                    df = pd.read_csv(filename)
                    dfs[filename] = df
                    print(f"Loaded {filename} with columns: {', '.join(df.columns)}")
                except Exception as e:
                    print(f"Error loading file {filename}: {e}")
        elif command.startswith("plot"):
            parts = command.split()
            if len(parts) < 3:
                print("Usage: plot <file1> [file2 ...] <column>")
                continue
            col = parts[-1]
            filenames = parts[1:-1]
            if not filenames:
                print("Provide at least one file before the column name.")
                continue
            missing = [f for f in filenames if f not in dfs]
            if missing:
                print(f"File(s) not loaded: {', '.join(missing)}. Use load_csv first.")
                continue
            missing_col = [f for f in filenames if col not in dfs[f].columns]
            if missing_col:
                print(f"Column '{col}' not found in: {', '.join(missing_col)}")
                continue

            fig = go.Figure()
            per_file_avgs = {}
            for fname in filenames:
                df = dfs[fname]
                y_numeric = pd.to_numeric(df[col], errors='coerce')
                x_vals = df.index.to_list()
                fig.add_trace(go.Scatter(x=x_vals, y=y_numeric, mode='lines', name=fname))
                avg_full = y_numeric.mean()
                per_file_avgs[fname] = avg_full
                # Initial full-range average line (will be replaced on zoom)
                fig.add_hline(y=avg_full, line_dash='dash', line_color='red',
                              annotation_text=f"{fname} Avg: {avg_full:.2f}", annotation_position='top left')

            fig.update_layout(title=f"Plot of {col} from {', '.join(filenames)}",
                              xaxis_title='Index', yaxis_title=col)

            # Simple JavaScript with comprehensive debugging
            custom_js = r"""<script>
(function(){
  function base64ToArrayBuffer(b64){
    try { const binary = atob(b64); const len = binary.length; const bytes = new Uint8Array(len); for (let i=0;i<len;i++) bytes[i]=binary.charCodeAt(i); return bytes.buffer; } catch(e){ return null; }
  }
  function decodeTypedArray(obj){
    if(!obj || !obj.bdata || !obj.dtype) return [];
    const buf = base64ToArrayBuffer(obj.bdata); if(!buf) return [];
    switch(obj.dtype){
      case 'f8': return Array.from(new Float64Array(buf));
      case 'f4': return Array.from(new Float32Array(buf));
      case 'i4': return Array.from(new Int32Array(buf));
      case 'i2': return Array.from(new Int16Array(buf));
      case 'i1': return Array.from(new Int8Array(buf));
      case 'u4': return Array.from(new Uint32Array(buf));
      case 'u2': return Array.from(new Uint16Array(buf));
      case 'u1': return Array.from(new Uint8Array(buf));
      default: return [];
    }
  }
  function toArray(data){
    if(Array.isArray(data)) return data;
    if(!data || typeof data!=='object') return [];
    if(Array.isArray(data._inputArray)) return data._inputArray; // plotly internal
    if(data._inputArray && typeof data._inputArray.length==='number') return Array.from(data._inputArray);
    if(data.bdata && data.dtype) return decodeTypedArray(data);
    // Fallback: if looks like plain object with numeric keys
    const keys = Object.keys(data).filter(k=>/^\d+$/.test(k)).sort((a,b)=>a-b);
    if(keys.length) return keys.map(k=>data[k]);
    return [];
  }
  function ensureButton(){
    if(document.getElementById('zoomAvgBtn')) return;
    const btn = document.createElement('button');
    btn.id='zoomAvgBtn';
    btn.textContent='🔍 CALC ZOOM AVG';
    Object.assign(btn.style,{position:'fixed',bottom:'20px',right:'20px',zIndex:9999,padding:'10px 16px',background:'#ff6b00',color:'#fff',border:'2px solid #fff',borderRadius:'8px',cursor:'pointer',fontWeight:'600',fontFamily:'sans-serif',boxShadow:'0 2px 6px rgba(0,0,0,.3)'});
    btn.onclick = calcZoomAvg;
    document.body.appendChild(btn);
  }
  function calcZoomAvg(){
    const plot = document.getElementsByClassName('plotly-graph-div')[0];
    if(!plot || !plot._fullLayout){ alert('Plot not ready yet'); return; }
    const xr = plot._fullLayout.xaxis.range; if(!xr){ alert('No x-axis range'); return; }
    const xMin = xr[0], xMax = xr[1];
    if(!plot.data || !plot.data.length){ alert('No traces'); return; }

    const shapes = (plot.layout.shapes||[]).filter(s=>!s.name || !s.name.startsWith('zoom_avg_'));
    const annotations = (plot.layout.annotations||[]).filter(a=>!a.name || !a.name.startsWith('zoom_ann_'));

    let any=false; let msg='Zoom Averages ('+xMin.toFixed(2)+' to '+xMax.toFixed(2)+')\n\n';
    plot.data.forEach((trace, idx)=>{
      const xArr = toArray(trace.x);
      const yArr = toArray(trace.y);
      if(!xArr.length || !yArr.length || xArr.length!==yArr.length){
        console.warn('Trace', idx, 'data length mismatch', xArr.length, yArr.length, trace.name);
        return;
      }
      let sum=0, count=0;
      for(let i=0;i<xArr.length;i++){
        const xv = xArr[i];
        const yv = yArr[i];
        if(xv>=xMin && xv<=xMax && typeof yv==='number' && !Number.isNaN(yv)){
          sum+=yv; count++; }
      }
      if(count){
        any=true; const avg = sum/count; msg += (trace.name||('Trace '+idx))+': '+avg.toFixed(4)+' ('+count+' pts)\n';
        shapes.push({type:'line',xref:'x',yref:'y',x0:xMin,x1:xMax,y0:avg,y1:avg,line:{color:'red',width:3,dash:'solid'},name:'zoom_avg_'+idx});
        annotations.push({xref:'x',yref:'y',x:(xMin+xMax)/2,y:avg,text:'Zoom Avg '+avg.toFixed(2),showarrow:false,font:{color:'red',size:12},bgcolor:'white',bordercolor:'red',borderwidth:1,opacity:0.9,name:'zoom_ann_'+idx});
      }
    });
    if(!any){ alert('No data points in zoom window'); return; }
    Plotly.relayout(plot,{shapes,annotations});
    alert(msg);
  }
  function init(){ if(document.readyState==='complete'){ ensureButton(); } else { window.addEventListener('load', ensureButton); } }
  setTimeout(init, 400);
})();
</script>"""

            import tempfile, threading, webbrowser
            with tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w', encoding='utf-8') as tmp:
                html = fig.to_html(config={'scrollZoom': True}, include_plotlyjs='cdn', full_html=True)
                if '</body>' in html:
                    html = html.replace('</body>', custom_js + '\n</body>')
                else:
                    html += custom_js
                tmp.write(html)
                url = 'file://' + os.path.abspath(tmp.name)
                threading.Thread(target=webbrowser.open, args=(url,), daemon=True).start()
                print(f"Interactive plot opened for column '{col}' across {len(filenames)} file(s). Zoom to update averages.")
        elif command.startswith("regression"):
            import re
            from sklearn.linear_model import LinearRegression
            import numpy as np
            parts = command.split()
            if len(parts) < 2:
                print("Usage: regression <column> [param1=val1 param2=val2 ...]")
                continue
            col = parts[1]
            # Parse extra params
            params = {}
            for p in parts[2:]:
                if '=' in p:
                    k, v = p.split('=', 1)
                    params[k] = v
            # Use all loaded files
            if not dfs:
                print("No CSVs loaded. Use load_csv first.")
                continue
            # Concatenate all dataframes
            all_df = pd.concat(dfs.values(), ignore_index=True)
            if col not in all_df.columns:
                print(f"Column '{col}' not found in loaded data.")
                continue
            y = pd.to_numeric(all_df[col], errors='coerce')
            # Use index as X by default, or param X=colname
            if 'X' in params and params['X'] in all_df.columns:
                X = pd.to_numeric(all_df[params['X']], errors='coerce').values.reshape(-1,1)
                print(f"Using column '{params['X']}' as X.")
            else:
                X = np.arange(len(y)).reshape(-1,1)
                print("Using row index as X.")
            # Remove NaNs
            mask = ~np.isnan(y) & ~np.isnan(X.flatten())
            X = X[mask]
            y = y[mask]
            if len(y) < 2:
                print("Not enough data for regression.")
                continue
            model = LinearRegression()
            model.fit(X, y)
            print(f"Regression result for column '{col}':")
            print(f"  Intercept: {model.intercept_}")
            print(f"  Slope: {model.coef_[0]}")
            if hasattr(model, 'score'):
                print(f"  R^2 score: {model.score(X, y)}")
            # Optionally plot regression
            if params.get('plot', 'false').lower() == 'true':
                import plotly.graph_objects as go
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=X.flatten(), y=y, mode='markers', name='Data'))
                y_pred = model.predict(X)
                fig.add_trace(go.Scatter(x=X.flatten(), y=y_pred, mode='lines', name='Regression'))
                fig.update_layout(title=f"Regression of {col}", xaxis_title=params.get('X', 'Index'), yaxis_title=col)
                import tempfile, threading, webbrowser, os
                with tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w', encoding='utf-8') as tmp:
                    html = fig.to_html(config={'scrollZoom': True}, include_plotlyjs='cdn', full_html=True)
                    tmp.write(html)
                    url = 'file://' + os.path.abspath(tmp.name)
                    threading.Thread(target=webbrowser.open, args=(url,), daemon=True).start()
                    print(f"Regression plot opened in browser.")
            print("Regression analysis complete.")
            continue
        elif command in ("exit", "quit"):
            print("Exiting csv-mcp server.")
            break
        else:
            print("Unknown command. Available: load_csv <file1> [file2 ...], plot <file1> [file2 ...] <column>, exit, quit")

if __name__ == "__main__":
    main()
