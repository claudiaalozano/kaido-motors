import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {Presentation, PresentationFile} from 'file:///C:/Users/Usuario/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs';

const ROOT='C:/kaido-motors';
const BUILD=ROOT+'/tmp/ppt_5_diapositivas';
const SKILL='C:/Users/Usuario/.codex/plugins/cache/openai-primary-runtime/presentations/26.1013.11914/skills/presentations';
const PY='C:/Users/Usuario/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
const FINAL=ROOT+'/output/presentacion/Kaido_A013_5_diapositivas.pptx';
const utils=await import(pathToFileURL(SKILL+'/container_tools/artifact_tool_utils.mjs').href);
const FONT=utils.resolvePresentationFont({fontFamily:'Arial'});
const P=Presentation.create({slideSize:{width:1600,height:900}});
const C={ink:'#142B40',muted:'#566775',blue:'#176CA4',teal:'#087F7B',orange:'#D87836',red:'#AD3C3C',light:'#EFF4F6',line:'#D7E0E4',white:'#FFFFFF'};
const source='Fuente principal: C:/Users/Usuario/Desktop/Resumen_ejecutivo_Kaido_A013.docx.\nContraste: C:/kaido-motors/prevision_A013.ipynb (modelo final, celdas 57 a 77).';
function text(s,str,x,y,w,h,size=30,color=C.ink,bold=false,align='left'){
 const a=s.shapes.add({geometry:'textbox',name:str.slice(0,55),position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 a.text=str;a.text.style={typeface:FONT,fontSize:size,color,bold,alignment:align,verticalAlignment:'top',autoFit:'none',insets:0};return a;
}
function base(title,subtitle,n){const s=P.slides.add();s.background.fill=C.white;text(s,title,80,58,1440,85,56,C.ink,true);text(s,subtitle,80,151,1440,74,28,C.muted);text(s,`${n} / 5`,1445,847,75,30,20,C.muted,false,'right');return s;}
function table(s,values,x,y,w,h,widths,size=27){
 const t=s.tables.add({rows:values.length,columns:values[0].length,left:x,top:y,width:w,height:h,columnWidths:widths,values});
 t.styleOptions={headerRow:false,bandedRows:false};t.borders.assign({fill:C.white,width:0});
 for(let r=0;r<values.length;r++)for(let c=0;c<values[0].length;c++){
  const cell=t.getCell(r,c);cell.fill=r===0?C.ink:(r%2===0?C.light:C.white);
  cell.text.style={typeface:FONT,fontSize:size,color:r===0?C.white:C.ink,bold:r===0,alignment:c===0?'left':'right',verticalAlignment:'middle',insets:{left:14,right:14,top:7,bottom:7}};
 }
 return t;
}
function chart(s,type,config){const a=s.charts.add(type,config);utils.applyPresentationChartFont(a,{fontFamily:FONT});return a;}
const axis={textStyle:{typeface:FONT,fontSize:24,fill:C.muted},line:{fill:C.line,width:1}};
const labels={showValue:true,position:'outEnd',numberFormatCode:'#,##0',textStyle:{typeface:FONT,fontSize:27,bold:true,fill:C.ink}};

// 1. Context and clean demand, rather than a separate cover.
{
const s=base('La demanda real de Kaido en A012','Kaido Motors España. Plan de demanda y producción de A013',1);
text(s,'23.175',80,261,430,112,98,C.ink,true);
text(s,'matriculaciones en A012',80,382,440,45,30,C.muted);
text(s,'+8,5 % frente a A011',80,438,440,43,30,C.blue,true);
text(s,'20.706',590,261,440,112,98,C.teal,true);
text(s,'ventas sin automatriculaciones',590,382,460,80,30,C.muted);
text(s,'+6,0 % frente a A011',590,475,440,43,30,C.teal,true);
text(s,'−3,1 %',1120,261,420,112,98,C.orange,true);
text(s,'variación de enero a julio',1120,382,400,80,30,C.muted);
text(s,'Periodo comparable sin adelantos\nni caídas posteriores',1120,475,400,85,27,C.muted);
text(s,'10,7 % de automatriculaciones',80,603,650,52,34,C.ink,true);
text(s,'Son matriculaciones de la marca o de los concesionarios. Las excluimos de la demanda de clientes.',80,666,650,130,30,C.muted);
text(s,'Compras adelantadas al cierre del año',850,603,670,52,34,C.ink,true);
text(s,'Noviembre y diciembre concentran el crecimiento. Parte de esas compras corresponde a la demanda de A013.',850,666,670,130,30,C.muted);
s.speakerNotes.text=source+'\n\nGuion: El punto de partida son 23.175 matriculaciones, pero para medir la demanda de clientes quitamos las automatriculaciones. Quedan 20.706 ventas. Aunque esta cifra crece un 6 %, la comparación está afectada por el adelanto de compras al final del año. En enero a julio, el periodo que el resumen considera comparable sin adelantos ni caídas posteriores en ambos años, la demanda baja un 3,1 %. Esta comparación parcial ayuda a interpretar A012, pero no equivale por sí sola a reconstruir toda su demanda anual sin sucesos. También hay que considerar posibles restricciones de stock.';
}

// 2. Final market/segment/share model and forecasts from the executive summary.
{
const s=base('Previsión de demanda de Kaido en A013','Mercado total × peso de cada segmento × cuota de Kaido',2);
table(s,[['Segmento','Pesimista','Central','Optimista'],['SUV medio','5.483','7.020','9.091'],['SUV pequeño','5.186','6.632','8.582'],['Compacto','2.670','3.164','3.805'],['SUV compacto','2.433','3.108','4.018'],['Pequeño','1.020','1.301','1.680'],['Berlina media','315','373','449'],['Descapotable','300','355','427'],['TOTAL','17.407','21.953','28.051']],80,252,815,495,[290,175,175,175],26);
text(s,'Demanda anual prevista, coches',950,238,570,45,30,C.ink,true);
chart(s,'bar',{position:{left:940,top:305,width:600,height:410},categories:['Pesimista','Central','Optimista'],series:[{name:'Demanda de Kaido',values:[17407,21953,28051],points:[{idx:0,fill:C.orange},{idx:1,fill:C.blue},{idx:2,fill:C.teal}]}],barOptions:{direction:'column',grouping:'clustered',varyColors:true,gapWidth:100},hasLegend:false,dataLabels:labels,xAxis:{...axis},yAxis:{...axis,min:0,max:32000,majorUnit:10000,numberFormatCode:'#,##0',majorGridlines:{fill:C.line,width:1}},chartFill:C.white,plotAreaFill:C.white});
text(s,'Validación del mercado total A010–A012: WAPE del 6,5 % al 10,6 %.\nLanzamientos: supuesto de mejora relativa de cuota del 10 % desde abril.',80,783,1440,64,26,C.muted);
s.speakerNotes.text=source+'\n\nGuion: Tras comparar el SARIMAX inicial por segmento, el modelo final separa el mercado total de la distribución entre segmentos. El total utiliza economía, calendario y sucesos. El peso del segmento recoge tendencias recientes, y la cuota convierte mercado en demanda de Kaido, quitando automatriculaciones. Los códigos nuevos reciben un aumento relativo del 10 % de cuota desde abril en el central. Es un supuesto basado en el análisis del resumen. Las validaciones del mercado total dan WAPE 6,5 %, 10,6 % y 10,5 % para A010, A011 y A012. Estos errores son del mercado total, no de la demanda de Kaido ni de cada segmento. Las salidas guardadas muestran avisos de convergencia en algunos ajustes, que deben revisarse antes de cerrar el modelo. El Word y el notebook tienen pequeñas diferencias numéricas, por lo que se mantienen las cifras del Word en toda la presentación. Los totales de demanda se obtienen antes del redondeo y pueden diferir en una unidad de la suma de segmentos. Escenarios y supuestos: config/supuestos.json. El mercado total central del resumen es 774.665 coches frente a 902.437 en A012. La demanda no equivale a las ventas que la simulación consigue atender.';
}

// 3. Central arrivals, explicitly distinguishing arrivals from factory production.
{
const s=base('Plan central: unas 20.000 llegadas a la red','Demanda prevista de 21.953 coches. Parte se atiende con el stock inicial.',3);
table(s,[['Segmento','Demanda','Llegadas'],['SUV medio','7.020','6.845'],['SUV pequeño','6.632','6.955'],['Compacto','3.164','2.202'],['SUV compacto','3.108','2.325'],['Pequeño','1.301','987'],['Berlina media','373','275'],['Descapotable','355','393'],['TOTAL','21.953','19.982']],80,246,710,477,[320,195,195],27);
text(s,'Llegadas mensuales del plan central',850,244,670,45,30,C.ink,true);
chart(s,'line',{position:{left:840,top:305,width:690,height:365},categories:['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'],series:[{name:'Llegadas mensuales',values:[2059,2059,1874,1076,1542,1846,2005,621,1308,1948,1662,1982],line:{fill:C.blue,width:4},marker:{symbol:'circle',size:7,fill:C.blue}}],hasLegend:false,xAxis:{...axis,textStyle:{typeface:FONT,fontSize:21,fill:C.muted}},yAxis:{...axis,min:0,max:2500,majorUnit:500,numberFormatCode:'#,##0',majorGridlines:{fill:C.line,width:1}},chartFill:C.white,plotAreaFill:C.white});
text(s,'Enero y febrero: 2.059 coches/mes ya comprometidos.\nCompacto y SUV compacto: prioridad a vender el stock existente.',850,691,670,90,27,C.ink);
text(s,'Medias simuladas. La suma de cifras redondeadas es 19.982; la media total sin redondear es 19.988.\nLas llegadas se revisan a tres meses vista. La fabricación debe desplazarse según ese plazo.',80,790,1440,62,24,C.muted);
s.speakerNotes.text=source+'\n\nGuion: El objetivo central es atender unas 22.000 unidades de demanda con aproximadamente 20.000 llegadas y el stock inicial. No es una resta exacta entre fabricación y demanda: hay stock final, ventas perdidas y transfers. La tabla mide llegadas a la red durante A013, no la fecha de fabricación en origen. Enero y febrero ya vienen en camino. Se toma como supuesto su volumen, estimado desde el wholesale reciente. Las decisiones nuevas afectan a la llegada de dentro de tres meses. El compacto y el SUV compacto tienen cerca de cuatro meses de stock inicial, por lo que al principio se reducen las entradas. La suma de los valores redondeados del Word es 19.982 y la media agregada del escenario central es 19.988. Ambas son aproximadamente 20.000. La curva mensual también procede de cifras redondeadas.\n\nDetalle mensual de llegadas por segmento (enero a diciembre): MSUV 578,578,349,508,719,678,786,219,508,676,586,660; SSUV 357,357,1389,444,620,752,597,166,404,608,541,720; C 453,453,0,1,21,117,223,81,151,250,202,250; CSUV 489,489,0,0,22,97,235,87,156,275,239,236; B 122,122,1,101,108,116,96,47,54,74,69,77; MD 26,26,0,10,32,47,31,9,23,29,18,24; S 34,34,135,12,20,39,37,12,12,36,7,15. Los totales se calculan antes del redondeo.';
}

// 4. Scenario outcome table preserves the distinction between demand and realized sales.
{
const s=base('Resultados y riesgo de los tres escenarios','Medias de 1.000 simulaciones. Plan central inicial con revisiones a tres meses.',4);
const t=table(s,[['Resultado A013','Pesimista','Central','Optimista'],['Coches vendidos','16.816','21.393','27.084'],['Ventas, intervalo 5 %–95 %','14.217–19.929','18.670–24.540','23.965–30.455'],['Llegadas a la red','15.127','19.988','25.608'],['Stock medio, coches','2.756','2.508','2.173'],['Stock >90 días al cierre','175','103','66'],['Coste del stock, M€','2,4','2,4','2,3'],['Gasto comercial VM, M€','36,1','45,2','56,8'],['Margen CVP, M€','−2,7','77,1','98,6']],80,243,1440,513,[570,290,290,290],29);
for(let c=0;c<4;c++){t.getCell(8,c).text.style={typeface:FONT,fontSize:31,color:c===1?C.red:C.ink,bold:true,alignment:c===0?'left':'right',insets:{left:14,right:14,top:7,bottom:7},verticalAlignment:'middle'};}
text(s,'CVP antes del coste del stock. En el central: 413 ventas perdidas y 307 transfers.\nStock medio equivalente a 1,9 / 1,4 / 0,9 meses de venta, respectivamente.',80,790,1440,67,25,C.muted);
s.speakerNotes.text=source+'\n\nGuion: Se mantiene la misma política inicial basada en el central. Cada escenario cambia la demanda y permite revisiones solo sobre lo que aún se puede modificar. Por eso las llegadas finales difieren entre escenarios. Las ventas realizadas son menores que la demanda prevista, ya que la disponibilidad y las decisiones operativas limitan lo que se consigue vender. El central realiza 21.393 ventas y deja 77,1 millones de CVP antes del coste del stock. Al restar aproximadamente 2,4 millones de coste del stock, quedan unos 74,7 millones. El pesimista da pérdidas incluso antes de ese coste. Los intervalos 5 %–95 % son percentiles de las ventas simuladas bajo los supuestos del modelo, no garantías. Los cambios de producción, suministro y márgenes están sujetos a los supuestos de la simulación. La tabla del Word incluye también costes de ventas perdidas y transfers. En el central, ventas perdidas 413 coches y 0,8 millones de CVP; transfers 307 coches y 0,3 millones de coste. Pesimista: 437 ventas perdidas y 280 transfers; optimista: 804 y 602. Se mantienen las cifras del Word aunque las últimas ejecuciones del notebook difieran ligeramente.';
}

// 5. Financial implications and concrete monthly decision rules.
{
const s=base('Prioridades comerciales y riesgo de CO₂','Rentabilidad por coche y señales para revisar el plan',5);
table(s,[['Segmento','CVP/coche','Con CO₂','Prioridad'],['SUV medio','5.714 €','1.511 €','Impulsar'],['SUV compacto','3.798 €','1.886 €','Vender stock y crecer'],['Berlina media','3.760 €','1.678 €','Mantener'],['SUV pequeño','2.568 €','−262 €','Vigilar prima'],['Compacto','1.187 €','−765 €','Contener'],['Pequeño','−69 €','−2.624 €','Contener'],['Descapotable','4.631 €','138 €','Reducir stock viejo']],80,244,955,466,[285,175,175,320],26);
text(s,'≈50 M€',1100,248,420,105,84,C.red,true);
text(s,'Impacto de la prima de CO₂\nen el escenario pesimista',1100,363,420,100,30,C.ink,true);
text(s,'Revisión mensual',1100,496,420,47,32,C.ink,true);
text(s,'Ventas: desviación >15 %\ndurante dos meses.\n\nStock >2 meses: frenar.\nStock <0,5 meses: valorar\ntransfers.',1100,557,420,245,27,C.muted);
text(s,'SUV medio: perder una venta supone 5.714 € de CVP.\nMantener un coche un mes cuesta 60 €, más el posible VM adicional por antigüedad.',80,763,970,89,28,C.muted);
s.speakerNotes.text=source+'\n\nGuion: El SUV medio y el SUV compacto concentran aproximadamente el 68 % del margen según el resumen, aunque en CSUV primero hay que vender el stock que ya está en la red. El pequeño pierde dinero por coche incluso antes de la prima y no conviene impulsar su volumen. El compacto tiene margen reducido y necesita contener el stock. La berlina media conserva rentabilidad unitaria, pero tiene poca demanda. En el descapotable la prioridad es evitar envejecimiento. La prima de CO2 resta alrededor de 50 millones en el pesimista y lleva el CVP a unos −2,7 millones. Los valores unitarios son CVP histórico medio antes del coste de stock, con o sin la prima hipotética. El coste de perder una venta de SUV medio es 5.714 euros, frente a 60 euros por mantener un coche un mes. La comparación de unas 95 veces solo aplica a ese horizonte de un mes y excluye VM adicional, acumulación de costes y transfer. Los umbrales de revisión del 15 %, dos meses de stock y medio mes son propuestas de gestión del resumen, no leyes del modelo ni condiciones impuestas por el caso. También se vigilan la antigüedad, el paro, la confianza, la decisión de la matriz sobre CO2 y los lanzamientos.';
}

await fs.mkdir(BUILD,{recursive:true});
await fs.mkdir(path.dirname(FINAL),{recursive:true});
const candidate=BUILD+'/candidate.pptx';
await (await PresentationFile.exportPptx(P)).save(candidate);
await fs.writeFile(BUILD+'/deck.json',JSON.stringify(P.toProto()));
for(let i=0;i<P.slides.items.length;i++){
 const b=await P.export({slide:P.slides.items[i],format:'png',scale:1});
 await fs.writeFile(`${BUILD}/slide-${i+1}.png`,new Uint8Array(await b.arrayBuffer()));
}
console.log('Draft and five previews written');
const result=await utils.finalizePresentation({workspaceDir:ROOT,candidatePath:candidate,finalPath:FINAL,pythonExecutable:PY,integrityValidatorPath:SKILL+'/container_tools/inspect_presentation_package_integrity.py',layoutValidatorPath:SKILL+'/container_tools/inspect_presentation_layout_geometry.py',layoutArgs:['--expected-slide-size-emu','15240000,8572500','--validate-bullet-geometry','--validate-heading-fit'],explicitTotalSlideCount:5,requiredNativeTableOwnerSlides:[2,3,4,5],requiredNativeChartOwnerSlides:[2,3],materializeLiteralChartWorkbooks:true,fontPolicy:{basis:'design',families:[FONT]},verifyArtifactToolImport:true,receiptPath:BUILD+'/validation.json'});
console.log(JSON.stringify(result));
