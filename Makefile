.PHONY: deploy
deploy:
	rm -rf deploy
	mkdir deploy
	cp -r src/ deploy
	cd deploy && rm -rf .git && git init && git add -A && git commit -m "init" && git remote add dokku dokku@apps.cs61a.org:slack && git push --force dokku master
	rm -rf deploy
