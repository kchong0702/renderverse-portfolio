export const addWordNewLine = (str, breakpoint = 40) => {
  var words = str.split(" ");
  var numChars = 0;
  var mult = 1;

  for (var i = 0; i < words.length; i++) {
    numChars += words[i].length;

    if (numChars > breakpoint * mult) {
      words[i] += "\n";
      mult++;
    }
  }
  return words.join(" ").replaceAll("\n ", "\n");
};

export const delay = async (promise) => {
  await new Promise((resolve) => {
    setTimeout(resolve, 2500);
  });
  return promise;
};

export const megaDelay = async (promise) => {
  await new Promise((resolve) => {
    setTimeout(resolve, 4000);
  });
  return promise;
};
