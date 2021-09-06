import IPython
from google.colab import output
from skimage.io import imsave
from skimage.transform import resize
import codecs
import numpy as np
import json, os
from IPython.display import HTML, Javascript
import matplotlib.pyplot as plt
from base64 import b64decode
from skimage.io import imread

class StreetViewCapture:

    def __init__(self, apikey, h=400, w=600, labels=None, datapath="data", 
                 geojson_file='zona.geojson'):
        global capture
        capture = []
        if labels is None:
            labels = [
              "supermercado", "talleres carros/motos", "parqueadero", "tienda", "carnicería/fruver", "licorera",
              "electrónica/cómputo", "ferretería", "muebles/tapicería",
              "electrodomésticos", "deporte", "ropa", "zapatería", "farmacia", 
              "puesto móvil/toldito", "hotel", "café/restaurante", "bar", 
              "belleza/barbería/peluquería", "animales"
            ]

        self.h = h
        self.w = w
        self.labels = labels
        self.datapath = datapath
        self.last_capture = None
        self.apikey = apikey

        if geojson_file is not None and os.path.isfile(geojson_file):
            with open(geojson_file, "r") as f:
              self.geojson_str = json.dumps(json.load(f))
        else:
            self.geojson_str = "NOGEOJSON"
            print ("NO ZONE FOUND. UPLOAD A FILE NAMED zone.geojson TO DISPLAY YOUR LABELING ZONE")
        

        os.makedirs(datapath, exist_ok=True)

        label_html_template = """
                  <label>
                      <input id="label_%s" type="checkbox" />
                      <span>%s</span>
                  </label>
        """
        labels_html = "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;".join([label_html_template%(i,i) for i in labels])

        self.form_html = f"""
<table>
  <tr>
    <td><div id="map"/></td>
    <td><div id="street_view"/></td>
  </tr>  
  <tr>
    <td><div id="status"></div>
        <br/>
        <img id="capture_img" width="300px"/>
        <div id="metadata_show"></div>
    </td>
    <td>
    
    <table>
      <tr>
        <td>
          <a id="acquire_btn" onclick="acquire()" class="waves-effect waves-light btn">acquire</a>
          &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
        </td>
        <td width=px>
            {labels_html}
        </td>
      </tr>
      </table>
    </td>
  </tr>  
</table>
      """
        self.form_html = self.form_html.replace("\n", "")
        
        self.full_html = """

<!-- Compiled and minified CSS -->
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/materialize/1.0.0/css/materialize.min.css">

<!-- Compiled and minified JavaScript -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/materialize/1.0.0/js/materialize.min.js"></script>


<script src="https://maps.google.com/maps/api/js?key=%s"></script>

<script>
elem = document.createElement('div')
elem.setAttributid=('id', 'mapframe')
document.querySelector("#output-area").appendChild(elem);

elem.innerHTML='%s'

</script>

  <script type="text/javascript">

    // --------------------
    // this forces all canvas to allow grabbing the pixles
    // https://groups.google.com/g/webgl-dev-list/c/QaCSENwlNhY?pli=1
		var getContext = HTMLCanvasElement.prototype.getContext;
		HTMLCanvasElement.prototype.getContext = function(){

			if( arguments[ 1 ] ) arguments[ 1 ].preserveDrawingBuffer = true;
			var context = getContext.apply( this, arguments );
			return context;

		}
    // --------------------

    function buf2hex(buffer) { // buffer is an ArrayBuffer
      return [...new Uint8Array(buffer)]
          .map(x => x.toString(16).padStart(2, '0'))
          .join('');
    }

    async function acquire() {
        var status = document.getElementById("status")

        // get street view metadata
        metadata = window.street_view.getPov()
        loc = window.street_view.getLocation()
        metadata['lat'] = loc.latLng.lat()
        metadata['lon'] = loc.latLng.lng()
        
        // get selected labels
        var label_elems = document.querySelectorAll('[id^="label_"]');
        labels = []
        for (label_elem of label_elems) {
          if (label_elem.checked) {
            labels.push(label_elem.id.substring(6))
          }
        }


        if (labels.length==0) {
            status.innerHTML = "<b><font color='red'>must choose at least one label</font></b>"
            return 
        }

        metadata['labels'] = labels

        // get streetview image
        var celem = document.getElementsByClassName("widget-scene-canvas")[0]
        imgdata = celem.toDataURL("image/png")

        var canvas = celem.getContext("webgl", {preserveDrawingBuffer: true});
        if (canvas) {
          canvas_type="gl"
        } else {
          canvas_type="2d"
        }

        var button = document.getElementById("acquire_btn")
        button.style.visibility = 'hidden'
        status.innerHTML = "acquiring image, please wait ... "
        metadata['canvas_type'] = canvas_type
        msg = await google.colab.kernel.invokeFunction(
                'notebook.getimg', // The callback name.
                [metadata, imgdata],
                {}); // kwargs
        msg = msg.data['text/plain']
        button.style.visibility = 'visible'
        status.innerHTML = "last image acquired<br/>"+msg;

        for (label_elem of label_elems) {
          label_elem.checked = false
        }


        capture_img = document.getElementById("capture_img")
        capture_img.setAttribute("src",
              celem.toDataURL("image/png"));

        metadata_elem = document.getElementById("metadata_show")
        metadata_str = JSON.stringify(metadata).replace(/,/g, "\\n")
        metadata_elem.innerHTML = "<pre>"+metadata_str+"</pre>"
        console.log("done call")

    }

    function initialize() {
      console.log("starting")
      var startpos = {lat: 6.26744, lng: -75.5692};

      var geojson_str = '%s'
      if (!geojson_str.includes("NOGEOJSON")) {
        var geojson = JSON.parse(geojson_str)
        p = geojson['features'][0]['geometry']['coordinates'][0][0]
        startpos = {lat: p[1], lng:p[0]}
      }

      var map = new google.maps.Map(
        document.getElementById("map"),
        {
          center: startpos,
          zoom: 14,
        }
      );

      if (!geojson_str.includes("NOGEOJSON")) {
        map.data.addGeoJson(geojson);
        map.data.setStyle({
            fillColor: 'green',
            strokeWeight: 1,
            fillOpacity: 0.1
        });
      }
      google.maps.streetViewViewer = 'photosphere';
      var panorama = new google.maps.StreetViewPanorama(
        document.getElementById('street_view'), {
          position: startpos,
          pov: {heading: 0, pitch: -4.57, zoom: 0.06}
      });
      window.street_view = panorama
      map.setStreetView(panorama);
    }
  </script>

  
<script>
document.getElementById("street_view").style.height = "%spx";
document.getElementById("street_view").style.width = "%spx";
document.getElementById("map").style.height = "%spx";
document.getElementById("map").style.width = "%spx";

initialize()

</script>
"""%(self.apikey, self.form_html, self.geojson_str, self.h, self.w, self.h, self.w)

    def getimg(self, metadata, imgdata):

          header, encoded = imgdata.split(",", 1)
          data = b64decode(encoded)
          fname = f"/tmp/{np.random.randint(100000)}.png"
          with open(fname, "wb") as f:
              f.write(data)
          img = imread(fname)

          if img.shape[:2]!=(self.h,self.w):
            img = resize(img, (self.h,self.w))
            img = (img*255).astype(np.uint8)

          fname = f"{self.datapath}/{metadata['lat']:.6f}_{metadata['lon']:.6f}_{metadata['heading']:.1f}"
          imsave(fname+".png", img)

          with open(fname+".json", "w") as f:
            json.dump(metadata, f)
            
          with open(fname+".json", "r") as f:
            k = json.load(f)

          self.last_capture = {'metadata': metadata, 'img': img}

          return f"saved to &nbsp;&nbsp;&nbsp;<font color='red'><tt>{fname}</tt></font>&nbsp;&nbsp;&nbsp; with size <tt>{img.shape}</tt>"

    def show(self):

        output.register_callback('notebook.getimg', self.getimg)
        return HTML(self.full_html)


    def show_last_capture(self):
        if self.last_capture is not None:
            for k,v in self.last_capture['metadata'].items():
                print (f'{k:10s}',v)
            print()
            plt.imshow(self.last_capture['img'])


    def show_captures(self, n_cols=6):
        def subplots(n_imgs, n_cols, usizex=3, usizey=3 ):
            n_rows = n_imgs//n_cols + int(n_imgs%n_cols!=0)
            fig = plt.figure(figsize=(n_cols*usizex, n_rows*usizey))
            
            for i in range(n_imgs):
                ax = fig.add_subplot(n_rows, n_cols, i+1)
                yield ax
                
        from skimage.io import imread
        fnames = [i for i in os.listdir(self.datapath) if i.endswith(".png")]

        for fname, ax in zip(fnames, subplots(len(fnames), n_cols=n_cols, usizey=2)):
          fname = f"{self.datapath}/{fname}"
          img = imread(fname)
          ax.imshow(img)
          try:
            with open(fname[:-4]+".json", "r") as f:
              metadata = json.load(f)
            plt.title(" ".join(metadata['labels'])+"\n"+fname.split("/")[-1][:-4])
          except:
            plt.title("no metadata")
          plt.axis("off")
        plt.tight_layout()
