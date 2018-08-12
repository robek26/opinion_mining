function createCORSRequest(method, url, tf) {
  var xhr = new XMLHttpRequest();
  if ("withCredentials" in xhr) {

    xhr.open(method, url, tf);

  } else if (typeof XDomainRequest != "undefined") {

    xhr = new XDomainRequest();
    xhr.open(method, url);

  } else {

    xhr = null;

  }
  return xhr;
}










