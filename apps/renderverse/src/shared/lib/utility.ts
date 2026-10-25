export const addWordNewLine = (str: string, breakpoint = 40) => {
  const words = str.split(" ");
  let numChars = 0;
  let mult = 1;

  for (let i = 0; i < words.length; i++) {
    numChars += words[i].length;

    if (numChars > breakpoint * mult) {
      words[i] += "\n";
      mult++;
    }
  }
  return words.join(" ").replaceAll("\n ", "\n");
};

export const wait = (ms: number, signal?: AbortSignal) =>
  new Promise<void>((resolve, reject) => {
    const timer = setTimeout(resolve, ms);
    signal?.addEventListener(
      "abort",
      () => {
        clearTimeout(timer);
        reject(signal.reason);
      },
      { once: true },
    );
  });

export const delay = async <T>(promise: Promise<T>): Promise<T> => {
  await wait(2500);
  return promise;
};

export const megaDelay = async <T>(promise: Promise<T>): Promise<T> => {
  await wait(4000);
  return promise;
};
