function addInteractivity(evt) {

    var svg = evt.target;
    var edges = document.getElementsByClassName('edge');
    var nodes = document.getElementsByClassName('node');
    var clusters = document.getElementsByClassName('cluster');
    var selectedElement, offset, transform, nodrag, origmousepos;

    svg.addEventListener('mousedown', startDrag);
    svg.addEventListener('mousemove', drag);
    svg.addEventListener('mouseup', endDrag);
    svg.addEventListener('mouseleave', endDrag);
    svg.addEventListener('touchstart', startDrag);
    svg.addEventListener('touchmove', drag);
    svg.addEventListener('touchend', endDrag);
    svg.addEventListener('touchleave', endDrag);
    svg.addEventListener('touchcancel', endDrag);

    for (var i = 0; i < edges.length; i++) {
        edges[i].addEventListener('click', clickEdge);
    }

    for (var i = 0; i < nodes.length; i++) {
        nodes[i].addEventListener('click', clickNode);
    }

    var svg = document.querySelector('svg');
    var viewBox = svg.viewBox.baseVal;
    adjustViewBox(svg);

    function getMousePosition(evt) {
        var CTM = svg.getScreenCTM();
        if (evt.touches) { evt = evt.touches[0]; }
        return {
            x: (evt.clientX - CTM.e) / CTM.a,
            y: (evt.clientY - CTM.f) / CTM.d
        };
    }

    function startDrag(evt) {
        origmousepos = getMousePosition(evt);
        nodrag=true;
        selectedElement = evt.target.parentElement;
        if (selectedElement){
            offset = getMousePosition(evt);

            // Make sure the first transform on the element is a translate transform
            var transforms = selectedElement.transform.baseVal;

            if (transforms.length === 0 || transforms.getItem(0).type !== SVGTransform.SVG_TRANSFORM_TRANSLATE) {
                // Create an transform that translates by (0, 0)
                var translate = svg.createSVGTransform();
                translate.setTranslate(0, 0);
                selectedElement.transform.baseVal.insertItemBefore(translate, 0);
            }

            // Get initial translation
            transform = transforms.getItem(0);
            offset.x -= transform.matrix.e;
            offset.y -= transform.matrix.f;
        }
    }

    function drag(evt) {
        if (selectedElement) {
            evt.preventDefault();
            var coord = getMousePosition(evt);
            transform.setTranslate(coord.x - offset.x, coord.y - offset.y);
        }
    }

    function endDrag(evt) {
            <!-- comment out the following line if you wnat drags to stay in place, with this line they snap back to their original position after drag end -->
            //if statement to avoid the header section being affected by the translate (0,0)
        if (selectedElement){
            if (selectedElement.classList.contains('header')){
                selectedElement = false;
            } else {
                selectedElement = false;
                transform.setTranslate(0,0);
            }
        }
        var currentmousepos=getMousePosition(evt);
        if (currentmousepos.x===origmousepos.x|currentmousepos.y===origmousepos.y){
            nodrag=true;
        } else {
            nodrag=false;
        }

    }

    function clickEdge() {
        if (nodrag) {
            if (this.classList.contains("edge-highlight")){
                this.classList.remove("edge-highlight");
                this.classList.remove("text-highlight-edges");
            }
            else {
                this.classList.add("edge-highlight");
                this.classList.add("text-highlight-edges");
                animateEdge(this);
            }
        }
    }

    function clickNode() {
        if (nodrag) {
            var nodeName = this.childNodes[1].textContent;
            // Escape special characters in the node name
            var nodeNameEscaped = nodeName.replace(/[-[\]{}()*+!<=:?.\/\\^$|#\s,]/g, '\\$&');

            var patroon = new RegExp('^' + nodeNameEscaped + '->|->' + nodeNameEscaped + '$|' + nodeNameEscaped + '--|--' + nodeNameEscaped + '$')

            if (this.classList.contains("node-highlight")) {
                this.classList.remove("node-highlight");
                this.classList.remove("text-highlight-nodes");
                var edges = document.getElementsByClassName('edge');
                for (var i = 0; i < edges.length; i++) {
                    if (patroon.test(edges[i].childNodes[1].textContent)) {
                        edges[i].classList.remove("edge-highlight");
                        edges[i].classList.remove("text-highlight-edges");
                    }
                }
            } else {
                this.classList.add("node-highlight");
                this.classList.add("text-highlight-nodes");
                var edges = document.getElementsByClassName('edge');
                for (var i = 0; i < edges.length; i++) {
                    if (patroon.test(edges[i].childNodes[1].textContent)) {
                        edges[i].classList.add("edge-highlight");
                        edges[i].classList.add("text-highlight-edges");
                        animateEdge(edges[i]);
                    }
                }
            }
        }
    }

    function animateEdge(edge){
        var path = edge.querySelector('path');
        var polygon = edge.querySelector('polygon');
        var length = path.getTotalLength();
        // Clear any previous transition
        path.style.transition = path.style.WebkitTransition = 'none';
        if (polygon){polygon.style.transition = polygon.style.WebkitTransition = 'none';};
        // Set up the starting positions
        path.style.strokeDasharray = length + ' ' + length;
        path.style.strokeDashoffset = length;
        if(polygon){polygon.style.opacity='0';};
        // Trigger a layout so styles are calculated & the browser
        // picks up the starting position before animating
        path.getBoundingClientRect();
        // Define our transition
        path.style.transition = path.style.WebkitTransition =
            'stroke-dashoffset 2s ease-in-out';
        if (polygon){polygon.style.transition = polygon.style.WebkitTransition =
                     'fill-opacity 1s ease-in-out 2s';};
        // Go!
        path.style.strokeDashoffset = '0';
        if (polygon){setTimeout(function(){polygon.style.opacity='1';},2000)};
    }
}

function adjustViewBox(svg) {
    var viewBoxParts = svg.getAttribute("viewBox").split(" ");
    var newYMin = parseFloat(viewBoxParts[1]) - 30; // Adjust this value as needed
    var newYMax = parseFloat(viewBoxParts[3]) + 30; // Adjust this value as needed
    var newXMax = Math.max(parseFloat(viewBoxParts[2]),240);
    var newViewBox = viewBoxParts[0] + " " + newYMin + " " + newXMax + " " + newYMax;
    svg.setAttribute("viewBox", newViewBox);
}
