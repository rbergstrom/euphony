<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" dir="ltr" lang="en-us" xml:lang="en-us">
	<head>
		<title>euphony - pairing</title>
		<script type="text/javascript" src="http://ajax.googleapis.com/ajax/libs/jquery/1.3.2/jquery.min.js"></script>
		<script type="text/javascript">
			function updateRemotes() {
				$('option').remove();
				$.getJSON('/web/pairing/remotes', function(data) {
					for (k in data.remotes) {
						$('#remotes').append(
							$('<option/>').attr('value', k).html(data.remotes[k])
						);
					}
				});
			}
			$(document).ready(function() {
				updateRemotes();
				$('#refresh').click(updateRemotes);
			});
		</script>
		<style type="text/css">
			* {
				font-size: 12px;
				font-family: Verdana;
			}
			div {
				margin-bottom: 10px;
			}
			label {
				display: block;
				margin-bottom: 2px;
			}

			input#code {
				width: 4em;
			}
		</style>
	</head>
	<body>
		<form action="" method="post">
			<div>
				<label for="remotes">Available Remotes:</label>
				<select id="remotes" name="remotes" size="5"></select>
			</div>
			<div>
				<label for="code">Pairing Code:</label>
				<input type="text" maxlength="4" name="code" id="code" />
				<input type="submit" value="Pair" />
				<input type="button" value="Refresh" id="refresh">
			</div>
		</form>
	</body>
</html>

