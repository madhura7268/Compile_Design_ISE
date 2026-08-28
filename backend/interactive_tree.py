import json

def get_node_description(node_name):
    # A simple heuristic to return descriptions based on node names
    name = node_name.lower()
    if 'program' in name:
        return "The root of the Abstract Syntax Tree. It contains the entire sequence of statements."
    elif 'vardeclaration' in name:
        return "Allocates memory for a new variable and specifies its data type."
    elif 'assignment' in name:
        return "Assigns a computed value or literal to an existing variable."
    elif 'ifstatement' in name:
        return "A control flow node that evaluates a condition to decide the execution path."
    elif 'condition' in name:
        return "The boolean expression evaluated to determine the execution path."
    elif 'whilestatement' in name:
        return "A loop construct that repeats execution as long as the condition holds true."
    elif 'operator' in name:
        return "Performs an arithmetic or logical operation on its child nodes (operands)."
    elif 'identifier' in name:
        return "A reference to a variable stored in the Symbol Table."
    elif 'literal' in name:
        return "A raw constant value (e.g. integer, string, boolean)."
    elif 'block' in name:
        return "A grouped sequence of statements."
    elif 'print' in name:
        return "Outputs the evaluated expression to the console/system."
    elif 'return' in name:
        return "Terminates execution of a function and returns a value."
    else:
        return f"Represents the '{node_name}' construct in the AST."

def add_descriptions_to_tree(node):
    # recursively add 'desc' field
    if not node:
        return None
    node['desc'] = get_node_description(node.get('name', ''))
    if 'children' in node:
        for child in node['children']:
            add_descriptions_to_tree(child)
    return node

def render_interactive_tree(ast_json):
    """
    Returns an HTML string containing the ECharts interactive tree.
    """
    if ast_json:
        # Create a deep copy or just modify in place since it's a dict generated for visualization anyway
        add_descriptions_to_tree(ast_json)
        
    chart_data = json.dumps(ast_json)
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <!-- Load ECharts -->
        <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
        <style>
            body, html {{ margin: 0; padding: 0; width: 100%; height: 100%; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: transparent; }}
            #main {{ width: 100%; height: 600px; overflow: hidden; }}
            #tooltip {{
                position: absolute;
                bottom: 20px;
                right: 20px;
                background-color: rgba(30, 27, 75, 0.95);
                color: white;
                padding: 15px 20px;
                border-radius: 8px;
                border: 1px solid #4F46E5;
                max-width: 320px;
                display: none;
                box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5);
                z-index: 1000;
                backdrop-filter: blur(4px);
            }}
            #tooltip h3 {{ margin: 0 0 8px 0; font-size: 16px; color: #a5b4fc; font-weight: 600; }}
            #tooltip p {{ margin: 0; font-size: 14px; line-height: 1.5; color: #e2e8f0; }}
            .close-btn {{
                position: absolute;
                top: 8px;
                right: 12px;
                cursor: pointer;
                color: #94a3b8;
                font-size: 14px;
                transition: color 0.2s;
            }}
            .close-btn:hover {{ color: white; }}
        </style>
    </head>
    <body>
        <div id="main"></div>
        <div id="tooltip">
            <span class="close-btn" onclick="document.getElementById('tooltip').style.display='none'">✖</span>
            <h3 id="tt-title">Node</h3>
            <p id="tt-desc">Description</p>
        </div>
        <script>
            var chartDom = document.getElementById('main');
            var myChart = echarts.init(chartDom, 'dark', {{ renderer: 'canvas' }});
            
            var data = {chart_data};

            var option = {{
                backgroundColor: 'transparent',
                tooltip: {{
                    trigger: 'item',
                    triggerOn: 'mousemove',
                    formatter: function (info) {{
                        return '<div style="max-width:250px;white-space:normal;"><b>' + info.name + '</b><br/>' + (info.data.desc || '') + '</div>';
                    }}
                }},
                series: [
                    {{
                        type: 'tree',
                        orient: 'TB',
                        data: [data],
                        top: '15%',
                        left: '5%',
                        bottom: '15%',
                        right: '5%',
                        symbol: 'circle',
                        symbolSize: 14,
                        itemStyle: {{
                            color: '#4F46E5',
                            borderColor: '#818cf8',
                            borderWidth: 2
                        }},
                        lineStyle: {{
                            color: '#6366f1',
                            width: 2,
                            curveness: 0.5
                        }},
                        label: {{
                            position: 'top',
                            verticalAlign: 'middle',
                            align: 'center',
                            distance: 10,
                            fontSize: 14,
                            color: '#f8fafc',
                            backgroundColor: '#1e293b',
                            borderColor: '#334155',
                            borderWidth: 1,
                            borderRadius: 6,
                            padding: [6, 10],
                            shadowBlur: 4,
                            shadowColor: 'rgba(0,0,0,0.3)'
                        }},
                        leaves: {{
                            label: {{
                                position: 'bottom',
                                verticalAlign: 'middle',
                                align: 'center',
                                distance: 10
                            }}
                        }},
                        emphasis: {{
                            focus: 'descendant',
                            itemStyle: {{
                                color: '#a5b4fc',
                                borderColor: '#ffffff'
                            }}
                        }},
                        expandAndCollapse: true,
                        animationDuration: 550,
                        animationDurationUpdate: 750
                    }}
                ]
            }};

            myChart.setOption(option);
            
            // Add click listener for persistent floating tooltip
            myChart.on('click', function (params) {{
                var tt = document.getElementById('tooltip');
                var title = document.getElementById('tt-title');
                var desc = document.getElementById('tt-desc');
                
                title.innerText = params.name;
                desc.innerText = params.data.desc || 'No description available for this node.';
                tt.style.display = 'block';
            }});
            
            window.addEventListener('resize', function() {{
                myChart.resize();
            }});
        </script>
    </body>
    </html>
    """
    return html
