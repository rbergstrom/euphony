(function($, undefined) {
	getScaleFactor = function(w, h, mw, mh) {
		var dw = (mw > 0) ? w - mw : 0,
		    dh = (mh > 0) ? h - mh : 0;

		if (dw > 0 && dw >= dh) {
			return mw / w;
		} else if (dh > 0 && dh >= dw) {
			return mh / h;
		} else {
			return 1.0;
		}
	};

	addDXFilter = function(node, filter) {
		node.style.filter += ' progid:DXImageTransform.Microsoft.' + filter;
	};

	msieReflect = function(image, scaleFactor, options) {
		var reflection = document.createElement('img'),	
		    resizeFilter = 'Matrix(M11='+scaleFactor+',M22='+scaleFactor+',SizingMethod=\'auto expand\')',
			mirrorFilter = 'BasicImage(mirror=1,rotation=2)',
			alphaFilter = 'Alpha(style=1,finishOpacity=0,startx=0,starty=0,finishx=0,finishy='+(options.height*100)+',opacity='+(100*options.opacity)+')';

		reflection.src = image.src;
		
		addDXFilter(image, resizeFilter);
		addDXFilter(reflection, mirrorFilter);
		addDXFilter(reflection, resizeFilter);
		addDXFilter(reflection, alphaFilter);

		var container = $('<div/>')
			.attr('class', $(image).attr('class'))
			.addClass(options.cssClass)
			.css({
				'position': 'relative',
				'overflow': 'hidden',
				'height': image.height * scaleFactor * (1 + options.height)
			});
		
		$(image).wrap(container).css({
			'position': 'absolute',
			'top': 0,
			'left': 0
		}).after(
			$(reflection).css({
				'position': 'absolute',
				'top': image.height * scaleFactor,
				'left': 0
			})
		);
		return container;
	};

	$.fn.reflect = function(options) {
		this.each(function() {
			$.fn.reflect.add(this, options);
		});
		return this;
	};

	$.fn.reflect.defaults = {
		'height': 0.3,
		'opacity': 0.5,
		'cssClass': 'reflected',
		'maxWidth': -1,
		'maxHeight': -1
	};

	$.fn.reflect.fromURL = function(url, options) {
		return $('<img/>').load(function() {
			$.fn.reflect.add(this, options);
			$(this).unbind('load');
		}).attr('src', url);
	};

	$.fn.reflect.add = function(image, options) {
		var options = $.extend({}, $.fn.reflect.defaults, options),
			scaleFactor = getScaleFactor(image.width, image.height, options.maxWidth, options.maxHeight),
			imageHeight = image.height * scaleFactor,
			imageWidth = image.width * scaleFactor,
			reflectionHeight = imageHeight * options.height,
		    canvas = document.createElement('canvas'), ctx;

		if (canvas.getContext !== undefined) {
			ctx = canvas.getContext('2d');
		} else {
			return msieReflect(image, scaleFactor, options);
		}

		if ($(image).hasClass(options.cssClass)) { return $(image); }

		canvas.width = imageWidth;
		canvas.height = imageHeight + reflectionHeight;
		
		ctx.drawImage(image, 0, 0, imageWidth, imageHeight);
		
		ctx.save();
		ctx.translate(0, (imageHeight * 2) - 1);
		ctx.scale(1, -1);
		ctx.drawImage(image, 0, 0, imageWidth, imageHeight);
		ctx.restore();
		
		ctx.globalCompositeOperation = 'destination-out';

		var gradient = ctx.createLinearGradient(0, imageHeight, 0, imageHeight + reflectionHeight);
		gradient.addColorStop(1.0, 'rgba(255, 255, 255, 1.0)');
		gradient.addColorStop(0.0, 'rgba(255, 255, 255, ' + (1 - options.opacity) + ')');
		ctx.fillStyle = gradient;
		ctx.rect(0, imageHeight, imageWidth, imageHeight + (2 * reflectionHeight));
		ctx.fill();

		if (canvas.toDataURL !== undefined) {
			$(image).attr('src', canvas.toDataURL('image/png')).css({
				'width': canvas.width,
				'height': canvas.height
			}).addClass(options.cssClass);
		} else {
			$(image).replaceWith($(canvas).css({
				'width': canvas.width,
				'height': canvas.height
			})).addClass(options.cssClass);
		}
		return $(image);
	};
})(jQuery);

