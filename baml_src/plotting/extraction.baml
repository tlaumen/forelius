function ExtractDatasetFromFreeform(numbered_input: string) -> ExtractedDataset {
  client ForeliusClaudeHaiku45
  prompt #"
    Extract one column-oriented dataset from the numbered user input below.

    Numbered input:
    {{ numbered_input }}

    Extraction rules:
    - Return only data explicitly present in the input.
    - Do not invent rows, columns, values, units, labels, or assumptions.
    - Preserve original value strings exactly as written, including decimal commas, missing tokens, and non-finite tokens.
    - Use the input line numbers to set data_start_line and data_end_line for the extracted data region.
    - Use a column-oriented output: every column has a name, optional unit, data_type, and values array.
    - If the requested data appears in repeated sections with the same table structure, combine those tables into one dataset.
    - Include parent section labels needed to preserve context as repeated column values.
    - Do not stop after the first matching table when the request asks for data "per" group.
    - All columns must have the same number of values.
    - Use NUMBER only when values are intended as numeric measurements or coordinates.
    - Use confidence LOW when the data region or column structure is ambiguous.
    - Do not generate code.

    {{ ctx.output_format }}
  "#
}

test extract_dataset_dutch_measurements {
  functions [ExtractDatasetFromFreeform]
  args {
    numbered_input #"
1: Maak een zettingsgrafiek.
2: Diepte (m); Zettting (mm)
3: 0; 0
4: 1,5; 12,5
5: 2,0; -
    "#
  }
}

test extract_dataset_tabular_loads {
  functions [ExtractDatasetFromFreeform]
  args {
    numbered_input #"
1: Plot force against displacement.
2: displacement mm | force kN
3: 0 | 0
4: 5 | 10.5
5: 10 | 18.2
    "#
  }
}

test extract_dataset_bearing_capacity_results_per_pile {
  functions [ExtractDatasetFromFreeform]
  args {
    numbered_input #"
1: Extract the bearing capacity results per pile
2: 
3: [PRELIMINARY DESIGN RESULTS]
4: 2 : Dump for option Preliminary Design, Indication bearing capacity
5:   50 = Number of piletypes
6:    2 = Number of iterations
7:    1 = Number of CPTs
8: 
9: [PILE]
10: PileName = Rect 300x500 prefab
11: BetaFactor = 1.00
12: SFactor = 0.84
13: 
14: [ITERATION RESULTS]
15: [TABLE]
16: DataCount=2
17: [COLUMN INDICATION]
18: IterationIndex
19: CptIndex
20: Level
21: RbCalMax
22: RsCalMax
23: RcCalMax
24: RcD
25: FNsfRep
26: FNsfD
27: RcNetD
28: Hmv
29: CptName
30: [END OF COLUMN INDICATION]
31: [DATA]
32:   1   1   -15.00      886     2041     2927     2927        0        0     2927     0.00 'CPT 1'
33:   2   1   -16.00      886     2041     2927     2927        0        0     2927     0.00 'CPT 1'
34: [END OF DATA]
35: [END OF TABLE]
36: [END OF ITERATION RESULTS]
37: 
38: [NEN AVERAGE PILE FACTORS]
39: [TABLE]
40: DataCount=1
41: [COLUMN INDICATION]
42: CptIndex
43: AlphaSGemSg
44: AlphaSGemClp
45: AlphaPGem
46: CptName
47: [END OF COLUMN INDICATION]
48: [DATA]
49:   1  0.0100  0.0157  0.7000 'CPT 1'
50: [END OF DATA]
51: [END OF TABLE]
52: [END OF NEN AVERAGE PILE FACTORS]
53: 
54: [CALCULATION PARAMETERS BEARING PILES EC 7]
55: Ksi3Used = 1.0000
56: Ksi4Used = 1.0000
57: GammaBUsed = 1.0000
58: GammaSUsed = 1.0000
59: IsKsi3Used = 0
60: [END OF CALCULATION PARAMETERS BEARING PILES EC 7]
61: 
62: [END OF PILE]
63: 
64: [PILE]
65: PileName = Rect 300x500 bored
66: BetaFactor = 1.00
67: SFactor = 0.84
68: 
69: [ITERATION RESULTS]
70: [TABLE]
71: DataCount=2
72: [COLUMN INDICATION]
73: IterationIndex
74: CptIndex
75: Level
76: RbCalMax
77: RsCalMax
78: RcCalMax
79: RcD
80: FNsfRep
81: FNsfD
82: RcNetD
83: Hmv
84: CptName
85: [END OF COLUMN INDICATION]
86: [DATA]
87:   1   1   -15.00      443     2022     2465     2465        0        0     2465     0.00 'CPT 1'
88:   2   1   -16.00      443     2022     2465     2465        0        0     2465     0.00 'CPT 1'
89: [END OF DATA]
90: [END OF TABLE]
91: [END OF ITERATION RESULTS]
92: 
93: [NEN AVERAGE PILE FACTORS]
94: [TABLE]
95: DataCount=1
96: [COLUMN INDICATION]
97: CptIndex
98: AlphaSGemSg
99: AlphaSGemClp
100: AlphaPGem
101: CptName
102: [END OF COLUMN INDICATION]
103: [DATA]
104:   1  0.0060  0.0157  0.3500 'CPT 1'
105: [END OF DATA]
106: [END OF TABLE]
107: [END OF NEN AVERAGE PILE FACTORS]
108: 
109: [CALCULATION PARAMETERS BEARING PILES EC 7]
110: Ksi3Used = 1.0000
111: Ksi4Used = 1.0000
112: GammaBUsed = 1.0000
113: GammaSUsed = 1.0000
114: IsKsi3Used = 0
115: [END OF CALCULATION PARAMETERS BEARING PILES EC 7]
116: 
117: [END OF PILE]
118: 
119: [PILE]
120: PileName = Rect 300x500 user
121: BetaFactor = 0.90
122: SFactor = 0.80
123: 
124: [ITERATION RESULTS]
125: [TABLE]
126: DataCount=2
127: [COLUMN INDICATION]
128: IterationIndex
129: CptIndex
130: Level
131: RbCalMax
132: RsCalMax
133: RcCalMax
134: RcD
135: FNsfRep
136: FNsfD
137: RcNetD
138: Hmv
139: CptName
140: [END OF COLUMN INDICATION]
141: [DATA]
142:   1   1   -15.00      108      348      456      456        0        0      456     0.00 'CPT 1'
143:   2   1   -16.00      108      396      504      504        0        0      504     0.00 'CPT 1'
144: [END OF DATA]
145: [END OF TABLE]
146: [END OF ITERATION RESULTS]
147: 
148: [NEN AVERAGE PILE FACTORS]
149: [TABLE]
150: DataCount=1
151: [COLUMN INDICATION]
152: CptIndex
153: AlphaSGemSg
154: AlphaSGemClp
155: AlphaPGem
156: CptName
157: [END OF COLUMN INDICATION]
158: [DATA]
159:   1  0.0020  0.0030  0.1000 'CPT 1'
160: [END OF DATA]
161: [END OF TABLE]
162: [END OF NEN AVERAGE PILE FACTORS]
163: 
164: [CALCULATION PARAMETERS BEARING PILES EC 7]
165: Ksi3Used = 1.0000
166: Ksi4Used = 1.0000
167: GammaBUsed = 1.0000
168: GammaSUsed = 1.0000
169: IsKsi3Used = 0
170: [END OF CALCULATION PARAMETERS BEARING PILES EC 7]
171: 
172: [END OF PILE]
173: 
174: [PILE]
175: PileName = Rect 300x500 user low
176: BetaFactor = 0.90
177: SFactor = 0.80
178: 
179: [ITERATION RESULTS]
180: [TABLE]
181: DataCount=2
182: [COLUMN INDICATION]
183: IterationIndex
184: CptIndex
185: Level
186: RbCalMax
187: RsCalMax
188: RcCalMax
189: RcD
190: FNsfRep
191: FNsfD
192: RcNetD
193: Hmv
194: CptName
195: [END OF COLUMN INDICATION]
196: [DATA]
197:   1   1   -15.00      108      375      483      483        0        0      483     0.00 'CPT 1'
198:   2   1   -16.00      108      423      531      531        0        0      531     0.00 'CPT 1'
199: [END OF DATA]
200: [END OF TABLE]
201: [END OF ITERATION RESULTS]
202: 
203: [NEN AVERAGE PILE FACTORS]
204: [TABLE]
205: DataCount=1
206: [COLUMN INDICATION]
207: CptIndex
208: AlphaSGemSg
209: AlphaSGemClp
210: AlphaPGem
211: CptName
212: [END OF COLUMN INDICATION]
213: [DATA]
214:   1  0.0020  0.0030  0.1000 'CPT 1'
215: [END OF DATA]
216: [END OF TABLE]
217: [END OF NEN AVERAGE PILE FACTORS]
218: 
219: [CALCULATION PARAMETERS BEARING PILES EC 7]
220: Ksi3Used = 1.0000
221: Ksi4Used = 1.0000
222: GammaBUsed = 1.0000
223: GammaSUsed = 1.0000
224: IsKsi3Used = 0
225: [END OF CALCULATION PARAMETERS BEARING PILES EC 7]
226: 
227: [END OF PILE]
228: 
229: [PILE]
230: PileName = RectEnl 300x500 prefab
231: BetaFactor = 1.00
232: SFactor = 0.84
233: 
234: [ITERATION RESULTS]
235: [TABLE]
236: DataCount=2
237: [COLUMN INDICATION]
238: IterationIndex
239: CptIndex
240: Level
241: RbCalMax
242: RsCalMax
243: RcCalMax
244: RcD
245: FNsfRep
246: FNsfD
247: RcNetD
248: Hmv
249: CptName
250: [END OF COLUMN INDICATION]
251: [DATA]
252:   1   1   -15.00      886        0      886      886        0        0      886     0.00 'CPT 1'
253:   2   1   -16.00      886        0      886      886        0        0      886     0.00 'CPT 1'
254: [END OF DATA]
255: [END OF TABLE]
256: [END OF ITERATION RESULTS]
257: 
258: [NEN AVERAGE PILE FACTORS]
259: [TABLE]
260: DataCount=1
261: [COLUMN INDICATION]
262: CptIndex
263: AlphaSGemSg
264: AlphaSGemClp
265: AlphaPGem
266: CptName
267: [END OF COLUMN INDICATION]
268: [DATA]
269:   1  0.0000  0.0000  0.7000 'CPT 1'
270: [END OF DATA]
271: [END OF TABLE]
272: [END OF NEN AVERAGE PILE FACTORS]
273: 
274: [CALCULATION PARAMETERS BEARING PILES EC 7]
275: Ksi3Used = 1.0000
276: Ksi4Used = 1.0000
277: GammaBUsed = 1.0000
278: GammaSUsed = 1.0000
279: IsKsi3Used = 0
280: [END OF CALCULATION PARAMETERS BEARING PILES EC 7]
281: 
282: [END OF PILE]
283: 
284: [PILE]
285: PileName = RectEnl 300x500 user
286: BetaFactor = 0.80
287: SFactor = 0.90
288: 
289: [ITERATION RESULTS]
290: [TABLE]
291: DataCount=2
292: [COLUMN INDICATION]
293: IterationIndex
294: CptIndex
295: Level
296: RbCalMax
297: RsCalMax
298: RcCalMax
299: RcD
300: FNsfRep
301: FNsfD
302: RcNetD
303: Hmv
304: CptName
305: [END OF COLUMN INDICATION]
306: [DATA]
307:   1   1   -15.00      864      671     1535     1535        0        0     1535     0.00 'CPT 1'
308:   2   1   -16.00      864      743     1607     1607        0        0     1607     0.00 'CPT 1'
309: [END OF DATA]
310: [END OF TABLE]
    "#
  }
  @@assert({{ this.data_start_line > 20 }})
  @@assert({{ this.data_end_line > 100 }})
  @@assert({{ this.columns|selectattr("name", "equalto", "PileName")|list|length == 1 }})
  @@assert({{ ((this.columns|selectattr("name", "equalto", "PileName")|first).values|length) == 12 }})
  @@assert({{ ((this.columns|selectattr("name", "equalto", "Level")|first).values|length) == 12 }})
  @@assert({{ ((this.columns|selectattr("name", "equalto", "PileName")|first).values|select("equalto", "Rect 300x500 prefab")|list|length) == 2 }})
  @@assert({{ ((this.columns|selectattr("name", "equalto", "PileName")|first).values|select("equalto", "Rect 300x500 bored")|list|length) == 2 }})
  @@assert({{ ((this.columns|selectattr("name", "equalto", "PileName")|first).values|select("equalto", "Rect 300x500 user")|list|length) == 2 }})
  @@assert({{ ((this.columns|selectattr("name", "equalto", "PileName")|first).values|select("equalto", "Rect 300x500 user low")|list|length) == 2 }})
  @@assert({{ ((this.columns|selectattr("name", "equalto", "PileName")|first).values|select("equalto", "RectEnl 300x500 prefab")|list|length) == 2 }})
  @@assert({{ ((this.columns|selectattr("name", "equalto", "PileName")|first).values|select("equalto", "RectEnl 300x500 user")|list|length) == 2 }})
  @@assert({{ ((this.columns|selectattr("name", "equalto", "Level")|first).values|select("equalto", "-15.00")|list|length) == 6 }})
  @@assert({{ ((this.columns|selectattr("name", "equalto", "Level")|first).values|select("equalto", "-16.00")|list|length) == 6 }})
}
