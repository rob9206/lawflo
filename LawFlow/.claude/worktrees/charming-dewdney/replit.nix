{ pkgs }: {
  deps = [
    pkgs.python312
    pkgs.nodejs_20
    pkgs.nodePackages.npm
  ];
}
