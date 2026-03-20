#!/bin/bash

git fetch --tags

dev_tags=($(git for-each-ref --sort=-creatordate --format='%(refname:short)' refs/tags | grep '^dev' | head -n 2))
prod_tags=($(git for-each-ref --sort=-creatordate --format='%(refname:short)' refs/tags | grep '^v[0-9]' | head -n 2))

max_count=${#dev_tags[@]}
if [ ${#prod_tags[@]} -gt $max_count ]; then
    max_count=${#prod_tags[@]}
fi

printf "%-20s %-20s\n" "Dev" "Prod"
for ((i=0; i<max_count; i++)); do
    dev="${dev_tags[i]}"
    prod="${prod_tags[i]}"
    printf "%-20s %-20s\n" "${dev:-}" "${prod:-}"
done

read -p "Enter tag name: " tag
git tag -a "$tag" -m "$tag"
git push origin "$tag"